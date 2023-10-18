/*
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

#include <quic/common/WindowedCounter.h>
#include <quic/congestion_control/Bbr.h>
#include <quic/d6d/BinarySearchProbeSizeRaiser.h>
#include <quic/d6d/ConstantStepProbeSizeRaiser.h>
#include <quic/dsr/frontend/WriteFunctions.h>
#include <quic/fizz/server/handshake/FizzServerQuicHandshakeContext.h>
#include <quic/server/QuicServerTransport.h>
#include <quic/server/handshake/AppToken.h>
#include <quic/server/handshake/DefaultAppTokenValidator.h>
#include <quic/server/handshake/StatelessResetGenerator.h>

#include <algorithm>

namespace quic {

QuicServerTransport::QuicServerTransport(
    folly::EventBase* evb,
    std::unique_ptr<folly::AsyncUDPSocket> sock,
    ConnectionSetupCallback* connSetupCb,
    ConnectionCallback* connStreamsCb,
    std::shared_ptr<const fizz::server::FizzServerContext> ctx,
    std::unique_ptr<CryptoFactory> cryptoFactory,
    PacketNum startingPacketNum)
    : QuicServerTransport(
          evb,
          std::move(sock),
          connSetupCb,
          connStreamsCb,
          std::move(ctx),
          std::move(cryptoFactory)) {
  conn_->ackStates = AckStates(startingPacketNum);
}

QuicServerTransport::QuicServerTransport(
    folly::EventBase* evb,
    std::unique_ptr<folly::AsyncUDPSocket> sock,
    ConnectionSetupCallback* connSetupCb,
    ConnectionCallback* connStreamsCb,
    std::shared_ptr<const fizz::server::FizzServerContext> ctx,
    std::unique_ptr<CryptoFactory> cryptoFactory,
    bool useConnectionEndWithErrorCallback)
    : QuicTransportBase(
          evb,
          std::move(sock),
          useConnectionEndWithErrorCallback),
      ctx_(std::move(ctx)),
      observerContainer_(std::make_shared<SocketObserverContainer>(this)) {
  auto tempConn = std::make_unique<QuicServerConnectionState>(
      FizzServerQuicHandshakeContext::Builder()
          .setFizzServerContext(ctx_)
          .setCryptoFactory(std::move(cryptoFactory))
          .build());
  tempConn->serverAddr = socket_->address();
  serverConn_ = tempConn.get();
  conn_.reset(tempConn.release());
  conn_->observerContainer = observerContainer_;

  setConnectionSetupCallback(connSetupCb);
  setConnectionCallback(connStreamsCb);
  registerAllTransportKnobParamHandlers();
}

QuicServerTransport::~QuicServerTransport() {
  VLOG(10) << "Destroyed connection to client=" << *this;
  // The caller probably doesn't need the conn callback after destroying the
  // transport.
  resetConnectionCallbacks();
  closeImpl(
      QuicError(
          QuicErrorCode(LocalErrorCode::SHUTTING_DOWN),
          std::string("Closing from server destructor")),
      false);
}

QuicServerTransport::Ptr QuicServerTransport::make(
    folly::EventBase* evb,
    std::unique_ptr<folly::AsyncUDPSocket> sock,
    ConnectionSetupCallback* connSetupCb,
    ConnectionCallback* connStreamsCb,
    std::shared_ptr<const fizz::server::FizzServerContext> ctx,
    bool useConnectionEndWithErrorCallback) {
  return std::make_shared<QuicServerTransport>(
      evb,
      std::move(sock),
      connSetupCb,
      connStreamsCb,
      ctx,
      nullptr /* cryptoFactory */,
      useConnectionEndWithErrorCallback);
}

void QuicServerTransport::setRoutingCallback(
    RoutingCallback* callback) noexcept {
  routingCb_ = callback;
}

void QuicServerTransport::setHandshakeFinishedCallback(
    HandshakeFinishedCallback* callback) noexcept {
  handshakeFinishedCb_ = callback;
}

void QuicServerTransport::setOriginalPeerAddress(
    const folly::SocketAddress& addr) {
  conn_->originalPeerAddress = addr;
}

void QuicServerTransport::setServerConnectionIdParams(
    ServerConnectionIdParams params) noexcept {
  serverConn_->serverConnIdParams.assign(std::move(params));
}

void QuicServerTransport::setTransportStatsCallback(
    QuicTransportStatsCallback* statsCallback) noexcept {
  if (conn_) {
    conn_->statsCallback = statsCallback;
  }
}

void QuicServerTransport::setConnectionIdAlgo(
    ConnectionIdAlgo* connIdAlgo) noexcept {
  CHECK(connIdAlgo);
  if (serverConn_) {
    serverConn_->connIdAlgo = connIdAlgo;
  }
}

void QuicServerTransport::setServerConnectionIdRejector(
    ServerConnectionIdRejector* connIdRejector) noexcept {
  CHECK(connIdRejector);
  if (serverConn_) {
    serverConn_->connIdRejector = connIdRejector;
  }
}

void QuicServerTransport::onReadData(
    const folly::SocketAddress& peer,
    NetworkDataSingle&& networkData) {
  ServerEvents::ReadData readData;
  readData.peer = peer;
  readData.networkData = std::move(networkData);
  bool waitingForFirstPacket = !hasReceivedPackets(*conn_);
  uint64_t prevWritableBytes = serverConn_->writableBytesLimit
      ? *serverConn_->writableBytesLimit
      : std::numeric_limits<uint64_t>::max();
  onServerReadData(*serverConn_, readData);
  processPendingData(true);

  if (closeState_ == CloseState::CLOSED) {
    return;
  }
  if (!notifiedRouting_ && routingCb_ && conn_->serverConnectionId) {
    notifiedRouting_ = true;
    if (routingCb_) {
      routingCb_->onConnectionIdAvailable(
          shared_from_this(), *conn_->serverConnectionId);
    }
  }
  if (connSetupCallback_ && waitingForFirstPacket &&
      hasReceivedPackets(*conn_)) {
    connSetupCallback_->onFirstPeerPacketProcessed();
  }

  uint64_t curWritableBytes = serverConn_->writableBytesLimit
      ? *serverConn_->writableBytesLimit
      : std::numeric_limits<uint64_t>::max();

  // If we've increased our writable bytes limit after processing incoming data
  // and we were previously blocked from writing probes, fire the PTO alarm
  if (serverConn_->transportSettings.enableWritableBytesLimit &&
      serverConn_->numProbesWritableBytesLimited &&
      prevWritableBytes < curWritableBytes) {
    onPTOAlarm(*serverConn_);
    serverConn_->numProbesWritableBytesLimited = 0;
  }

  maybeWriteNewSessionTicket();
  maybeNotifyConnectionIdBound();
  maybeNotifyHandshakeFinished();
  maybeIssueConnectionIds();
  maybeStartD6DProbing();
  maybeNotifyTransportReady();
}

void QuicServerTransport::accept() {
  setIdleTimer();
  updateFlowControlStateWithSettings(
      conn_->flowControlState, conn_->transportSettings);
  serverConn_->serverHandshakeLayer->initialize(
      evb_, this, std::make_unique<DefaultAppTokenValidator>(serverConn_));
}

void QuicServerTransport::writeData() {
  if (!conn_->clientConnectionId || !conn_->serverConnectionId) {
    return;
  }
  auto version = conn_->version.value_or(*(conn_->originalVersion));
  const ConnectionId& srcConnId = *conn_->serverConnectionId;
  const ConnectionId& destConnId = *conn_->clientConnectionId;
  if (closeState_ == CloseState::CLOSED) {
    if (conn_->peerConnectionError &&
        hasReceivedPacketsAtLastCloseSent(*conn_)) {
      // The peer sent us an error, we are in draining state now.
      return;
    }
    if (hasReceivedPacketsAtLastCloseSent(*conn_) &&
        hasNotReceivedNewPacketsSinceLastCloseSent(*conn_)) {
      // We did not receive any new packets, do not sent a new close frame.
      return;
    }
    updateLargestReceivedPacketsAtLastCloseSent(*conn_);
    if (conn_->oneRttWriteCipher) {
      CHECK(conn_->oneRttWriteHeaderCipher);
      writeShortClose(
          *socket_,
          *conn_,
          destConnId,
          conn_->localConnectionError,
          *conn_->oneRttWriteCipher,
          *conn_->oneRttWriteHeaderCipher);
    }
    if (conn_->handshakeWriteCipher) {
      CHECK(conn_->handshakeWriteHeaderCipher);
      writeLongClose(
          *socket_,
          *conn_,
          srcConnId,
          destConnId,
          LongHeader::Types::Handshake,
          conn_->localConnectionError,
          *conn_->handshakeWriteCipher,
          *conn_->handshakeWriteHeaderCipher,
          version);
    }
    if (conn_->initialWriteCipher) {
      CHECK(conn_->initialHeaderCipher);
      writeLongClose(
          *socket_,
          *conn_,
          srcConnId,
          destConnId,
          LongHeader::Types::Initial,
          conn_->localConnectionError,
          *conn_->initialWriteCipher,
          *conn_->initialHeaderCipher,
          version);
    }
    return;
  }
  uint64_t packetLimit =
      (isConnectionPaced(*conn_)
           ? conn_->pacer->updateAndGetWriteBatchSize(Clock::now())
           : conn_->transportSettings.writeConnectionDataPacketsLimit);
  // At the end of this function, clear out any probe packets credit we didn't
  // use.
  SCOPE_EXIT {
    conn_->pendingEvents.numProbePackets = {};
  };
  if (conn_->initialWriteCipher) {
    auto& initialCryptoStream =
        *getCryptoStream(*conn_->cryptoState, EncryptionLevel::Initial);
    CryptoStreamScheduler initialScheduler(*conn_, initialCryptoStream);
    auto& numProbePackets =
        conn_->pendingEvents.numProbePackets[PacketNumberSpace::Initial];
    if ((numProbePackets && initialCryptoStream.retransmissionBuffer.size() &&
         conn_->outstandings.packetCount[PacketNumberSpace::Initial]) ||
        initialScheduler.hasData() ||
        (conn_->ackStates.initialAckState.needsToSendAckImmediately &&
         hasAcksToSchedule(conn_->ackStates.initialAckState))) {
      CHECK(conn_->initialWriteCipher);
      CHECK(conn_->initialHeaderCipher);

      auto res = writeCryptoAndAckDataToSocket(
          *socket_,
          *conn_,
          srcConnId /* src */,
          destConnId /* dst */,
          LongHeader::Types::Initial,
          *conn_->initialWriteCipher,
          *conn_->initialHeaderCipher,
          version,
          packetLimit);

      packetLimit -= res.packetsWritten;
      serverConn_->numHandshakeBytesSent += res.bytesWritten;
    }
    if (!packetLimit && !conn_->pendingEvents.anyProbePackets()) {
      return;
    }
  }
  if (conn_->handshakeWriteCipher) {
    auto& handshakeCryptoStream =
        *getCryptoStream(*conn_->cryptoState, EncryptionLevel::Handshake);
    CryptoStreamScheduler handshakeScheduler(*conn_, handshakeCryptoStream);
    auto& numProbePackets =
        conn_->pendingEvents.numProbePackets[PacketNumberSpace::Handshake];
    if ((conn_->outstandings.packetCount[PacketNumberSpace::Handshake] &&
         handshakeCryptoStream.retransmissionBuffer.size() &&
         numProbePackets) ||
        handshakeScheduler.hasData() ||
        (conn_->ackStates.handshakeAckState.needsToSendAckImmediately &&
         hasAcksToSchedule(conn_->ackStates.handshakeAckState))) {
      CHECK(conn_->handshakeWriteCipher);
      CHECK(conn_->handshakeWriteHeaderCipher);
      auto res = writeCryptoAndAckDataToSocket(
          *socket_,
          *conn_,
          srcConnId /* src */,
          destConnId /* dst */,
          LongHeader::Types::Handshake,
          *conn_->handshakeWriteCipher,
          *conn_->handshakeWriteHeaderCipher,
          version,
          packetLimit);

      packetLimit -= res.packetsWritten;
      serverConn_->numHandshakeBytesSent += res.bytesWritten;
    }
    if (!packetLimit && !conn_->pendingEvents.anyProbePackets()) {
      return;
    }
  }
  if (conn_->oneRttWriteCipher) {
    CHECK(conn_->oneRttWriteHeaderCipher);
    // TODO(yangchi): I don't know which one to prioritize. I can see arguments
    // both ways. I'm going with writing regular packets first since they
    // contain ack and flow control update and other important info.
    auto writeLoopBeginTime = Clock::now();
    packetLimit -= writeQuicDataToSocket(
                       *socket_,
                       *conn_,
                       srcConnId /* src */,
                       destConnId /* dst */,
                       *conn_->oneRttWriteCipher,
                       *conn_->oneRttWriteHeaderCipher,
                       version,
                       packetLimit,
                       writeLoopBeginTime)
                       .packetsWritten;
    if (packetLimit) {
      packetLimit -= writePacketizationRequest(
          *serverConn_,
          destConnId,
          packetLimit,
          *conn_->oneRttWriteCipher,
          writeLoopBeginTime);
    }

    // D6D probes should be paced
    if (packetLimit && conn_->pendingEvents.d6d.sendProbePacket) {
      writeD6DProbeToSocket(
          *socket_,
          *conn_,
          srcConnId,
          destConnId,
          *conn_->oneRttWriteCipher,
          *conn_->oneRttWriteHeaderCipher,
          version);
    }
  }
}

void QuicServerTransport::closeTransport() {
  if (!serverConn_->serverHandshakeLayer->isHandshakeDone()) {
    QUIC_STATS(conn_->statsCallback, onServerUnfinishedHandshake);
    if (handshakeFinishedCb_) {
      handshakeFinishedCb_->onHandshakeUnfinished();
      handshakeFinishedCb_ = nullptr;
    }
  }
  serverConn_->serverHandshakeLayer->cancel();
  // Clear out pending data.
  serverConn_->pendingZeroRttData.reset();
  serverConn_->pendingOneRttData.reset();
  onServerClose(*serverConn_);
}

void QuicServerTransport::unbindConnection() {
  if (routingCb_) {
    auto routingCb = routingCb_;
    routingCb_ = nullptr;
    CHECK(conn_->clientChosenDestConnectionId);
    if (conn_->serverConnectionId) {
      routingCb->onConnectionUnbound(
          this,
          std::make_pair(
              getOriginalPeerAddress(), *conn_->clientChosenDestConnectionId),
          conn_->selfConnectionIds);
    }
  }
}

bool QuicServerTransport::hasWriteCipher() const {
  return conn_->oneRttWriteCipher != nullptr;
}

bool QuicServerTransport::hasReadCipher() const {
  return conn_->readCodec != nullptr &&
      conn_->readCodec->getOneRttReadCipher() != nullptr;
}

std::shared_ptr<QuicTransportBase> QuicServerTransport::sharedGuard() {
  return shared_from_this();
}

void QuicServerTransport::setClientConnectionId(
    const ConnectionId& clientConnectionId) {
  conn_->clientConnectionId.assign(clientConnectionId);
  conn_->peerConnectionIds.emplace_back(
      clientConnectionId, kInitialSequenceNumber);
}

void QuicServerTransport::setClientChosenDestConnectionId(
    const ConnectionId& clientChosenDestConnectionId) {
  conn_->clientChosenDestConnectionId.assign(clientChosenDestConnectionId);
}

void QuicServerTransport::onCryptoEventAvailable() noexcept {
  try {
    VLOG(10) << "onCryptoEventAvailable " << *this;
    if (closeState_ != CloseState::OPEN) {
      VLOG(10) << "Got crypto event after connection closed " << *this;
      return;
    }
    updateHandshakeState(*serverConn_);
    processPendingData(false);
    // pending data may contain connection close
    if (closeState_ == CloseState::CLOSED) {
      return;
    }
    maybeWriteNewSessionTicket();
    maybeNotifyConnectionIdBound();
    maybeNotifyHandshakeFinished();
    maybeIssueConnectionIds();
    writeSocketData();
    maybeNotifyTransportReady();
  } catch (const QuicTransportException& ex) {
    VLOG(4) << "onCryptoEventAvailable() error " << ex.what() << " " << *this;
    closeImpl(QuicError(QuicErrorCode(ex.errorCode()), std::string(ex.what())));
  } catch (const QuicInternalException& ex) {
    VLOG(4) << "onCryptoEventAvailable() error " << ex.what() << " " << *this;
    closeImpl(QuicError(QuicErrorCode(ex.errorCode()), std::string(ex.what())));
  } catch (const std::exception& ex) {
    VLOG(4) << "read() error " << ex.what() << " " << *this;
    closeImpl(QuicError(
        QuicErrorCode(TransportErrorCode::INTERNAL_ERROR),
        std::string(ex.what())));
  }
}

void QuicServerTransport::handleTransportKnobParams(
    const TransportKnobParams& params) {
  for (const auto& param : params) {
    auto maybeParamHandler = transportKnobParamHandlers_.find(param.id);
    TransportKnobParamId knobParamId = TransportKnobParamId::UNKNOWN;
    if (TransportKnobParamId::_is_valid(param.id)) {
      knobParamId = TransportKnobParamId::_from_integral(param.id);
    }
    if (maybeParamHandler != transportKnobParamHandlers_.end()) {
      (maybeParamHandler->second)(this, param.val);
      QUIC_STATS(conn_->statsCallback, onTransportKnobApplied, knobParamId);
    } else {
      QUIC_STATS(conn_->statsCallback, onTransportKnobError, knobParamId);
    }
  }
}

void QuicServerTransport::processPendingData(bool async) {
  // The case when both 0-rtt and 1-rtt pending data are ready to be processed
  // but neither had been shouldn't happen
  std::unique_ptr<std::vector<ServerEvents::ReadData>> pendingData;
  if (conn_->readCodec && conn_->readCodec->getOneRttReadCipher()) {
    pendingData = std::move(serverConn_->pendingOneRttData);
    // It's possible that 0-rtt packets are received after CFIN, we are not
    // dealing with that much level of reordering.
    serverConn_->pendingZeroRttData.reset();
  } else if (conn_->readCodec && conn_->readCodec->getZeroRttReadCipher()) {
    pendingData = std::move(serverConn_->pendingZeroRttData);
  }
  if (pendingData) {
    // Move the pending data out so that we don't ever add new data to the
    // pending data.
    VLOG_IF(10, !pendingData->empty())
        << "Processing pending data size=" << pendingData->size() << " "
        << *this;
    auto func = [pendingData = std::move(pendingData)](auto self) {
      auto serverPtr = static_cast<QuicServerTransport*>(self.get());
      for (auto& pendingPacket : *pendingData) {
        serverPtr->onNetworkData(
            pendingPacket.peer,
            NetworkData(
                std::move(pendingPacket.networkData.data),
                pendingPacket.networkData.receiveTimePoint));
        if (serverPtr->closeState_ == CloseState::CLOSED) {
          // The pending data could potentially contain a connection close, or
          // the app could have triggered a connection close with an error. It
          // is not useful to continue the handshake.
          return;
        }
        // The app could have triggered a graceful close from the callbacks,
        // in which case we should continue with the handshake and processing
        // the reamining data because it could potentially have a FIN which
        // could end the graceful close.
      }
    };
    if (async) {
      runOnEvbAsync(std::move(func));
    } else {
      func(shared_from_this());
    }
  }
}

void QuicServerTransport::maybeWriteNewSessionTicket() {
  if (!newSessionTicketWritten_ && !ctx_->getSendNewSessionTicket() &&
      serverConn_->serverHandshakeLayer->isHandshakeDone()) {
    if (conn_->qLogger) {
      conn_->qLogger->addTransportStateUpdate(kWriteNst);
    }
    newSessionTicketWritten_ = true;
    AppToken appToken;
    appToken.transportParams = createTicketTransportParameters(
        conn_->transportSettings.idleTimeout.count(),
        conn_->transportSettings.maxRecvPacketSize,
        conn_->transportSettings.advertisedInitialConnectionWindowSize,
        conn_->transportSettings.advertisedInitialBidiLocalStreamWindowSize,
        conn_->transportSettings.advertisedInitialBidiRemoteStreamWindowSize,
        conn_->transportSettings.advertisedInitialUniStreamWindowSize,
        conn_->transportSettings.advertisedInitialMaxStreamsBidi,
        conn_->transportSettings.advertisedInitialMaxStreamsUni);
    appToken.sourceAddresses = serverConn_->tokenSourceAddresses;
    appToken.version = conn_->version.value();
    // If a client connects to server for the first time and doesn't attempt
    // early data, tokenSourceAddresses will not be set because
    // validateAndUpdateSourceAddressToken is not called in this case.
    // So checking if source address token is empty here and adding peerAddr
    // if so.
    // TODO accumulate recent source tokens
    if (appToken.sourceAddresses.empty()) {
      appToken.sourceAddresses.push_back(conn_->peerAddress.getIPAddress());
    }
    if (conn_->earlyDataAppParamsGetter) {
      appToken.appParams = conn_->earlyDataAppParamsGetter();
    }
    serverConn_->serverHandshakeLayer->writeNewSessionTicket(appToken);
  }
}

void QuicServerTransport::maybeNotifyConnectionIdBound() {
  // make this connId bound only when the keys are available
  if (!notifiedConnIdBound_ && routingCb_ && conn_->serverConnectionId &&
      serverConn_->serverHandshakeLayer->isHandshakeDone()) {
    notifiedConnIdBound_ = true;
    routingCb_->onConnectionIdBound(shared_from_this());
  }
}

void QuicServerTransport::maybeNotifyHandshakeFinished() {
  if (serverConn_->serverHandshakeLayer->isHandshakeDone()) {
    if (handshakeFinishedCb_) {
      handshakeFinishedCb_->onHandshakeFinished();
      handshakeFinishedCb_ = nullptr;
    }
    if (connSetupCallback_ && !handshakeDoneNotified_) {
      connSetupCallback_->onFullHandshakeDone();
      handshakeDoneNotified_ = true;
    }
  }
}

void QuicServerTransport::maybeIssueConnectionIds() {
  if (!conn_->transportSettings.disableMigration && !connectionIdsIssued_ &&
      serverConn_->serverHandshakeLayer->isHandshakeDone()) {
    connectionIdsIssued_ = true;
    CHECK(conn_->transportSettings.statelessResetTokenSecret.has_value());

    // If the peer specifies that they have a limit of 1,000,000 connection
    // ids then only issue a small number at first, since the server still
    // needs to be able to search through all issued ids for routing.
    const uint64_t maximumIdsToIssue = maximumConnectionIdsToIssue(*conn_);

    // Make sure size of selfConnectionIds is not larger than maximumIdsToIssue
    for (size_t i = conn_->selfConnectionIds.size(); i < maximumIdsToIssue;
         ++i) {
      auto newConnIdData = serverConn_->createAndAddNewSelfConnId();
      if (!newConnIdData.has_value()) {
        return;
      }

      CHECK(routingCb_);
      routingCb_->onConnectionIdAvailable(
          shared_from_this(), newConnIdData->connId);

      NewConnectionIdFrame frame(
          newConnIdData->sequenceNumber,
          0,
          newConnIdData->connId,
          *newConnIdData->token);
      sendSimpleFrame(*conn_, std::move(frame));
    }
  }
}

void QuicServerTransport::maybeNotifyTransportReady() {
  if (!transportReadyNotified_ && connSetupCallback_ && hasWriteCipher()) {
    if (conn_->qLogger) {
      conn_->qLogger->addTransportStateUpdate(kTransportReady);
    }
    transportReadyNotified_ = true;
    connSetupCallback_->onTransportReady();
  }
}

void QuicServerTransport::maybeStartD6DProbing() {
  if (!d6dProbingStarted_ && hasReadCipher() &&
      conn_->d6d.state == D6DMachineState::BASE) {
    d6dProbingStarted_ = true;
    auto& d6d = conn_->d6d;
    switch (conn_->transportSettings.d6dConfig.raiserType) {
      case ProbeSizeRaiserType::ConstantStep:
        d6d.raiser = std::make_unique<ConstantStepProbeSizeRaiser>(
            conn_->transportSettings.d6dConfig.probeRaiserConstantStepSize);
        break;
      case ProbeSizeRaiserType::BinarySearch:
        d6d.raiser = std::make_unique<BinarySearchProbeSizeRaiser>(
            kMinMaxUDPPayload, d6d.maxPMTU);
    }
    d6d.thresholdCounter =
        std::make_unique<WindowedCounter<uint64_t, uint64_t>>(
            std::chrono::microseconds(kDefaultD6DBlackholeDetectionWindow)
                .count(),
            kDefaultD6DBlackholeDetectionThreshold);
    d6d.currentProbeSize = d6d.basePMTU;
    // Start probing after some delay. This filters out short-lived
    // connections, for which probing is relatively expensive and less
    // valuable
    conn_->pendingEvents.d6d.sendProbeDelay = kDefaultD6DKickStartDelay;
    QUIC_STATS(conn_->statsCallback, onConnectionD6DStarted);

    if (getSocketObserverContainer() &&
        getSocketObserverContainer()
            ->hasObserversForEvent<
                SocketObserverInterface::Events::pmtuEvents>()) {
      getSocketObserverContainer()
          ->invokeInterfaceMethod<SocketObserverInterface::Events::pmtuEvents>(
              [](auto observer, auto observed) {
                observer->pmtuProbingStarted(observed);
              });
    }
  }
}

void QuicServerTransport::registerTransportKnobParamHandler(
    uint64_t paramId,
    std::function<void(QuicServerTransport*, uint64_t)>&& handler) {
  transportKnobParamHandlers_.emplace(paramId, std::move(handler));
}

void QuicServerTransport::setBufAccessor(BufAccessor* bufAccessor) {
  CHECK(bufAccessor);
  conn_->bufAccessor = bufAccessor;
}

#ifdef CCP_ENABLED
void QuicServerTransport::setCcpDatapath(struct ccp_datapath* datapath) {
  serverConn_->ccpDatapath = datapath;
}
#endif

const std::shared_ptr<const folly::AsyncTransportCertificate>
QuicServerTransport::getPeerCertificate() const {
  const auto handshakeLayer = serverConn_->serverHandshakeLayer;
  if (handshakeLayer) {
    return handshakeLayer->getState().clientCert();
  }
  return nullptr;
}

void QuicServerTransport::onTransportKnobs(Buf knobBlob) {
  if (knobBlob->length() > 0) {
    std::string serializedKnobs = std::string(
        reinterpret_cast<const char*>(knobBlob->data()), knobBlob->length());
    VLOG(4) << "Received transport knobs: " << serializedKnobs;
    auto params = parseTransportKnobs(serializedKnobs);
    if (params.hasValue()) {
      handleTransportKnobParams(*params);
    } else {
      QUIC_STATS(
          conn_->statsCallback,
          onTransportKnobError,
          TransportKnobParamId::UNKNOWN);
    }
  }
}

void QuicServerTransport::verifiedClientAddress() {
  if (serverConn_) {
    serverConn_->isClientAddrVerified = true;
    conn_->writableBytesLimit = folly::none;
  }
}

void QuicServerTransport::registerAllTransportKnobParamHandlers() {
  registerTransportKnobParamHandler(
      static_cast<uint64_t>(
          TransportKnobParamId::ZERO_PMTU_BLACKHOLE_DETECTION),
      [](QuicServerTransport* serverTransport, uint64_t val) {
        CHECK(serverTransport);
        auto server_conn = serverTransport->serverConn_;
        if (static_cast<bool>(val)) {
          server_conn->d6d.noBlackholeDetection = true;
          VLOG(3)
              << "Knob param received, pmtu blackhole detection is turned off";
        }
      });

  registerTransportKnobParamHandler(
      static_cast<uint64_t>(
          TransportKnobParamId::FORCIBLY_SET_UDP_PAYLOAD_SIZE),
      [](QuicServerTransport* serverTransport, uint64_t val) {
        CHECK(serverTransport);
        auto server_conn = serverTransport->serverConn_;
        if (static_cast<bool>(val)) {
          server_conn->udpSendPacketLen = server_conn->peerMaxUdpPayloadSize;
          VLOG(3)
              << "Knob param received, udpSendPacketLen is forcibly set to max UDP payload size advertised by peer";
        }
      });

  registerTransportKnobParamHandler(
      static_cast<uint64_t>(TransportKnobParamId::CC_ALGORITHM_KNOB),
      [](QuicServerTransport* serverTransport, uint64_t val) {
        CHECK(serverTransport);
        auto server_conn = serverTransport->serverConn_;
        auto cctype = static_cast<CongestionControlType>(val);
        VLOG(3) << "Knob param received, set congestion control type to "
                << congestionControlTypeToString(cctype);
        if (cctype == server_conn->congestionController->type()) {
          return;
        }
        if (cctype == CongestionControlType::CCP) {
          bool ccpAvailable = false;
#ifdef CCP_ENABLED
          ccpAvailable = server_conn->ccpDatapath != nullptr;
#endif
          if (!ccpAvailable) {
            LOG(ERROR) << "ccp not enabled on this server";
            return;
          }
        }
        server_conn->congestionController =
            server_conn->congestionControllerFactory->makeCongestionController(
                *server_conn, cctype);
      });

  registerTransportKnobParamHandler(
      static_cast<uint64_t>(TransportKnobParamId::CC_AGRESSIVENESS_KNOB),
      [](QuicServerTransport* serverTransport, uint64_t val) {
        CHECK(serverTransport);
        auto server_conn = serverTransport->serverConn_;
        if (val < 25 || val > 100) {
          LOG(ERROR)
              << "Invalid CC_AGRESSIVENESS_KNOB value received from client, value = "
              << val << ". Supported values are between 25,100 (inclusive)";
          return;
        }
        float targetFactor = val / 100.0f;
        VLOG(3)
            << "CC_AGRESSIVENESS_KNOB KnobParam received from client, setting congestion control aggressiveness to "
            << targetFactor;
        server_conn->congestionController->setBandwidthUtilizationFactor(
            targetFactor);
      });

  registerTransportKnobParamHandler(
      static_cast<uint64_t>(TransportKnobParamId::STARTUP_RTT_FACTOR_KNOB),
      [](QuicServerTransport* serverTransport, uint64_t val) {
        CHECK(serverTransport);
        auto server_conn = serverTransport->serverConn_;
        uint8_t numerator = (val / 100);
        uint8_t denominator = (val - (numerator * 100));
        VLOG(3) << "Knob param received, set STARTUP rtt factor to ("
                << unsigned(numerator) << "," << unsigned(denominator) << ")";
        server_conn->transportSettings.startupRttFactor =
            std::make_pair(numerator, denominator);
      });

  registerTransportKnobParamHandler(
      static_cast<uint64_t>(TransportKnobParamId::DEFAULT_RTT_FACTOR_KNOB),
      [](QuicServerTransport* serverTransport, uint64_t val) {
        CHECK(serverTransport);
        auto server_conn = serverTransport->serverConn_;
        auto numerator = (uint8_t)(val / 100);
        auto denominator = (uint8_t)(val - (numerator * 100));
        VLOG(3) << "Knob param received, set DEFAULT rtt factor to ("
                << unsigned(numerator) << "," << unsigned(denominator) << ")";
        server_conn->transportSettings.defaultRttFactor =
            std::make_pair(numerator, denominator);
      });

  registerTransportKnobParamHandler(
      static_cast<uint64_t>(TransportKnobParamId::NOTSENT_BUFFER_SIZE_KNOB),
      [](QuicServerTransport* serverTransport, uint64_t val) {
        CHECK(serverTransport);
        auto server_conn = serverTransport->serverConn_;
        VLOG(3) << "Knob param received, set total buffer space available to ("
                << unsigned(val) << ")";
        server_conn->transportSettings.totalBufferSpaceAvailable = val;
      });

  registerTransportKnobParamHandler(
      static_cast<uint64_t>(TransportKnobParamId::MAX_PACING_RATE_KNOB),
      [](QuicServerTransport* serverTransport, uint64_t val) {
        CHECK(serverTransport);
        VLOG(3) << "Knob param received, set max pacing rate to ("
                << unsigned(val) << " bytes per second)";
        serverTransport->setMaxPacingRate(val);
      });

  registerTransportKnobParamHandler(
      static_cast<uint64_t>(TransportKnobParamId::AUTO_BACKGROUND_MODE),
      [](QuicServerTransport* serverTransport, uint64_t val) {
        CHECK(serverTransport);
        uint64_t priorityThreshold = val / kPriorityThresholdKnobMultiplier;
        uint64_t utilizationPercent = val % kPriorityThresholdKnobMultiplier;
        float utilizationFactor = float(utilizationPercent) / 100.0f;
        VLOG(3) << fmt::format(
            "AUTO_BACKGROUND_MODE KnobParam received, enabling auto background mode "
            "with Priority Threshold={}, Utilization Factor={}",
            priorityThreshold,
            utilizationFactor);
        serverTransport->setBackgroundModeParameters(
            PriorityLevel(priorityThreshold), utilizationFactor);
      });

  registerTransportKnobParamHandler(
      static_cast<uint64_t>(TransportKnobParamId::CC_EXPERIMENTAL),
      [](QuicServerTransport* serverTransport, uint64_t val) {
        CHECK(serverTransport);
        auto server_conn = serverTransport->serverConn_;
        if (server_conn->congestionController) {
          auto enableExperimental = static_cast<bool>(val);
          server_conn->congestionController->setExperimental(
              enableExperimental);
          VLOG(3) << fmt::format(
              "CC_EXPERIMENTAL KnobParam received, setting experimental={} "
              "settings for congestion controller. Current congestion controller={}",
              enableExperimental,
              congestionControlTypeToString(
                  server_conn->congestionController->type()));
        }
      });

  registerTransportKnobParamHandler(
      static_cast<uint64_t>(TransportKnobParamId::SHORT_HEADER_PADDING_KNOB),
      [](QuicServerTransport* serverTransport, uint64_t val) {
        CHECK(serverTransport);
        serverTransport->serverConn_->transportSettings.paddingModulo = val;
        VLOG(3) << fmt::format(
            "SHORT_HEADER_PADDING_KNOB KnobParam received, setting paddingModulo={}",
            val);
      });

  registerTransportKnobParamHandler(
      static_cast<uint64_t>(TransportKnobParamId::ADAPTIVE_LOSS_DETECTION),
      [](QuicServerTransport* serverTransport, uint64_t val) {
        CHECK(serverTransport);
        auto server_conn = serverTransport->serverConn_;
        auto useAdaptiveLossThresholds = static_cast<bool>(val);
        server_conn->transportSettings.useAdaptiveLossThresholds =
            useAdaptiveLossThresholds;
        VLOG(3) << fmt::format(
            "ADAPTIVE_LOSS_DETECTION KnobParam received, UseAdaptiveLossThresholds is now set to {}",
            useAdaptiveLossThresholds);
      });

  registerTransportKnobParamHandler(
      static_cast<uint64_t>(TransportKnobParamId::PACER_EXPERIMENTAL),
      [](QuicServerTransport* serverTransport, uint64_t val) {
        CHECK(serverTransport);
        auto server_conn = serverTransport->serverConn_;
        if (server_conn->pacer) {
          auto enableExperimental = static_cast<bool>(val);
          server_conn->pacer->setExperimental(enableExperimental);
          VLOG(3) << fmt::format(
              "PACER_EXPERIMENTAL KnobParam received, "
              "setting experimental={} for pacer",
              enableExperimental);
        }
      });
  registerTransportKnobParamHandler(
      static_cast<uint64_t>(TransportKnobParamId::KEEPALIVE_ENABLED),
      [](QuicServerTransport* serverTransport, uint64_t val) {
        CHECK(serverTransport);
        auto server_conn = serverTransport->serverConn_;
        server_conn->transportSettings.enableKeepalive = static_cast<bool>(val);
        VLOG(3) << "KEEPALIVE_ENABLED KnobParam received: "
                << static_cast<bool>(val);
      });
  registerTransportKnobParamHandler(
      static_cast<uint64_t>(TransportKnobParamId::REMOVE_FROM_LOSS_BUFFER),
      [](QuicServerTransport* serverTransport, uint64_t val) {
        CHECK(serverTransport);
        auto server_conn = serverTransport->serverConn_;
        server_conn->transportSettings.removeFromLossBufferOnSpurious =
            static_cast<bool>(val);
        VLOG(3) << "REMOVE_FROM_LOSS_BUFFER KnobParam received: "
                << static_cast<bool>(val);
      });
}

QuicConnectionStats QuicServerTransport::getConnectionsStats() const {
  QuicConnectionStats connStats = QuicTransportBase::getConnectionsStats();
  if (serverConn_) {
    connStats.localAddress = serverConn_->serverAddr;
  }
  return connStats;
}

CipherInfo QuicServerTransport::getOneRttCipherInfo() const {
  return {
      *conn_->oneRttWriteCipher->getKey(),
      *serverConn_->serverHandshakeLayer->getState().cipher(),
      conn_->oneRttWriteHeaderCipher->getKey()->clone()};
}

} // namespace quic
