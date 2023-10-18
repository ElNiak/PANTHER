/*
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

#pragma once

#include <iostream>
#include <string>
#include <thread>

#include <glog/logging.h>

#include <folly/fibers/Baton.h>
#include <folly/io/async/ScopedEventBaseThread.h>

#include <quic/api/QuicSocket.h>
#include <quic/client/QuicClientTransport.h>
#include <quic/common/BufUtil.h>
#include <quic/common/test/TestClientUtils.h>
#include <quic/common/test/TestUtils.h>
#include <quic/fizz/client/handshake/FizzClientQuicHandshakeContext.h>
#include <quic/samples/echo/LogQuicStats.h>

#include <glog/logging.h>
#include <fizz/client/PskSerializationUtils.h>
#include <fizz/tool/FizzCommandCommon.h>
#include <folly/fibers/Baton.h>
#include <folly/io/async/ScopedEventBaseThread.h>
#include <fizz/util/KeyLogWriter.h>
#include <fizz/util/Parse.h>
#include <fizz/record/Types.h>
#include <folly/FileUtil.h>
#include <folly/Format.h>
#include <folly/io/async/SSLContext.h>
#include <fizz/crypto/aead/test/Mocks.h>
#include <fizz/protocol/clock/test/Mocks.h>
#include <quic/handshake/test/Mocks.h>

#include <iostream>
#include <string>
#include <thread>

#include <glog/logging.h>
#include <fizz/client/PskSerializationUtils.h>
#include <fizz/tool/FizzCommandCommon.h>
#include <folly/fibers/Baton.h>
#include <folly/io/async/ScopedEventBaseThread.h>
#include <fizz/util/KeyLogWriter.h>
#include <fizz/util/Parse.h>
#include <fizz/record/Types.h>
#include <folly/FileUtil.h>
#include <folly/Format.h>
#include <folly/io/async/SSLContext.h>
#include <fizz/crypto/aead/test/Mocks.h>
#include <fizz/protocol/clock/test/Mocks.h>
#include <quic/handshake/test/Mocks.h>
#include <quic/api/QuicSocket.h>
#include <quic/client/QuicClientTransport.h>
#include <quic/common/BufUtil.h>
#include <quic/common/test/TestUtils.h>
#include <quic/fizz/client/handshake/FizzClientQuicHandshakeContext.h>
#include <quic/samples/echo/LogQuicStats.h>

using namespace folly;
using namespace testing;

namespace quic {
namespace samples {

void tryWriteCert(const fizz::Cert* cert, io::Appender& appender) {
  if (auto opensslCert = dynamic_cast<const fizz::OpenSSLCert*>(cert)) {
    auto x509 = opensslCert->getX509();
    fizz::detail::writeBuf<uint32_t>(
        x509 ? folly::ssl::OpenSSLCertUtils::derEncode(*x509) : nullptr,
        appender);
  } else {
    fizz::detail::writeBuf<uint32_t>(nullptr, appender);
  }
}

class BasicPersistentQuicPskCache : public BasicQuicPskCache {
 public:
  BasicPersistentQuicPskCache(std::string save_file, std::string load_file)
      : saveFile_(save_file), loadFile_(load_file) {}

  void putPsk(const std::string& /* unused */, QuicCachedPsk psk) override {
    LOG(INFO) << "\n BasicPersistentQuicPskCache putPSK " << " \n";
    if (saveFile_.empty()) {
      return;
    }
    std::string serializedPsk = serializePsk(psk);
    if (folly::writeFile(serializedPsk, saveFile_.c_str())) {
      LOG(INFO) << "\n Saved PSK to " << saveFile_ << " \n";
    } else {
      LOG(ERROR) << "\n Unable to save PSK " << saveFile_ << " \n";
    }
  }

  folly::Optional<QuicCachedPsk> getPsk(const std::string& /* unused */) override {
    LOG(INFO) << "\n BasicPersistentQuicPskCache getPSK " << " \n";
    if (loadFile_.empty()) {
      return folly::none;
    }
    LOG(INFO) << "\n Loading PSK from " << loadFile_ << " \n";
    std::string serializedPsk;
    folly::readFile(loadFile_.c_str(), serializedPsk);
    try {
      QuicCachedPsk dpsk = deserializePsk(serializedPsk, fizz::OpenSSLFactory());
      return dpsk;
    } catch (const std::exception& e) {
      LOG(ERROR) << "Error deserializing: " << loadFile_ << "\n" << e.what();
      //throw;
      return folly::none;
    }
  }

  std::string serializePsk(const QuicCachedPsk& qpsk) {
    fizz::client::CachedPsk psk = qpsk.cachedPsk;
    uint64_t ticketIssueTime =
        std::chrono::duration_cast<std::chrono::milliseconds>(
            psk.ticketIssueTime.time_since_epoch())
            .count();
    uint64_t ticketExpirationTime =
        std::chrono::duration_cast<std::chrono::seconds>(
            psk.ticketExpirationTime.time_since_epoch())
            .count();
    uint64_t ticketHandshakeTime =
        std::chrono::duration_cast<std::chrono::milliseconds>(
            psk.ticketHandshakeTime.time_since_epoch())
            .count();

    LOG(INFO) << "\n serializePsk psk.ticketIssueTime "  << " \n";
    LOG(INFO) << ticketIssueTime;
    LOG(INFO) << ticketExpirationTime;
    LOG(INFO) << ticketHandshakeTime;
    // LOG(INFO) << "\n serializePsk psk.time now "  << " \n";
    // //LOG(INFO) <  psk.ticketIssueTime;
    // std::time_t now_c = std::chrono::system_clock::to_time_t(psk.ticketIssueTime);
    // std::tm now_tm = *std::localtime(&now_c);
    // char bbb[20];
    // LOG(INFO) << strftime(bbb, 20, "%d.%m.%Y %H:%M:%S", &now_tm);

    auto serialized = folly::IOBuf::create(0);
    folly::io::Appender appender(serialized.get(), 512);
    fizz::detail::writeBuf<uint16_t>(
        folly::IOBuf::wrapBuffer(folly::StringPiece(psk.psk)), appender);
    fizz::detail::writeBuf<uint16_t>(
        folly::IOBuf::wrapBuffer(folly::StringPiece(psk.secret)), appender);
    fizz::detail::write(psk.version, appender);
    fizz::detail::write(psk.cipher, appender);
    if (psk.group.has_value()) {
      fizz::detail::write(static_cast<uint8_t>(1), appender);
      fizz::detail::write(*psk.group, appender);
    } else {
      fizz::detail::write(static_cast<uint8_t>(0), appender);
    }
    fizz::detail::writeBuf<uint8_t>(
        psk.alpn ? folly::IOBuf::wrapBuffer(folly::StringPiece(*psk.alpn)) : nullptr,
        appender);
    fizz::detail::write(psk.ticketAgeAdd, appender); // + ticketIssueTime
    fizz::detail::write(ticketIssueTime, appender);
    fizz::detail::write(ticketExpirationTime, appender);
    tryWriteCert(psk.serverCert.get(), appender);
    tryWriteCert(psk.clientCert.get(), appender);
    fizz::detail::write(psk.maxEarlyDataSize, appender);
    fizz::detail::write(ticketHandshakeTime, appender);


    CachedServerTransportParameters transportParams = qpsk.transportParams;
    fizz::detail::write(transportParams.idleTimeout, appender);
    fizz::detail::write(transportParams.maxRecvPacketSize, appender);
    fizz::detail::write(transportParams.initialMaxData, appender);
    fizz::detail::write(transportParams.initialMaxStreamDataBidiLocal, appender);
    fizz::detail::write(transportParams.initialMaxStreamDataBidiRemote, appender);
    fizz::detail::write(transportParams.initialMaxStreamDataUni, appender);
    fizz::detail::write(transportParams.initialMaxStreamsBidi, appender);
    fizz::detail::write(transportParams.initialMaxStreamsUni, appender);

    std::string appParams = qpsk.appParams;
    fizz::detail::writeBuf<uint8_t>(
        folly::IOBuf::wrapBuffer(folly::StringPiece(appParams)),
        appender);

    return serialized->moveToFbString().toStdString();
  }

  QuicCachedPsk deserializePsk(
      const std::string& str,
      const fizz::Factory& factory) {
    auto buf = folly::IOBuf::wrapBuffer(str.data(), str.length());
    folly::io::Cursor cursor(buf.get());

    QuicCachedPsk qpsk;

    fizz::client::CachedPsk psk;
    psk.type = fizz::PskType::Resumption;

    std::unique_ptr<folly::IOBuf> pskData;
    fizz::detail::readBuf<uint16_t>(pskData, cursor);
    psk.psk = pskData->moveToFbString().toStdString();

    std::unique_ptr<folly::IOBuf> secretData;
    fizz::detail::readBuf<uint16_t>(secretData, cursor);
    psk.secret = secretData->moveToFbString().toStdString();

    fizz::detail::read(psk.version, cursor);
    fizz::detail::read(psk.cipher, cursor);
    uint8_t hasGroup;
    fizz::detail::read(hasGroup, cursor);
    if (hasGroup == 1) {
      fizz::NamedGroup group;
      fizz::detail::read(group, cursor);
      psk.group = group;
    }

    std::unique_ptr<folly::IOBuf> alpnData;
    fizz::detail::readBuf<uint8_t>(alpnData, cursor);
    if (!alpnData->empty()) {
      psk.alpn = alpnData->moveToFbString().toStdString();
    }

    fizz::detail::read(psk.ticketAgeAdd, cursor);

    LOG(INFO) << "\n deserializePsk psk.ticketAgeAdd "  << " \n";
    LOG(INFO) << psk.ticketAgeAdd;

    uint64_t ticketIssueTime;
    fizz::detail::read(ticketIssueTime, cursor);
    psk.ticketIssueTime = std::chrono::time_point<std::chrono::system_clock>(
        std::chrono::milliseconds(ticketIssueTime));

    LOG(INFO) << "\n deserializePsk psk.ticketIssueTime "  << " \n";
    LOG(INFO) << ticketIssueTime;
    //LOG(INFO) <  psk.ticketIssueTime;
    // std::time_t now_c = std::chrono::system_clock::to_time_t(psk.ticketIssueTime);
    // std::tm now_tm = *std::localtime(&now_c);
    // char bbb[20];
    // LOG(INFO) << strftime(bbb, 20, "%d.%m.%Y %H:%M:%S", &now_tm);

    uint64_t ticketExpirationTime;
    fizz::detail::read(ticketExpirationTime, cursor);
    psk.ticketExpirationTime = std::chrono::time_point<std::chrono::system_clock>(
        std::chrono::seconds(ticketExpirationTime));

    LOG(INFO) << ticketExpirationTime;

    fizz::CertificateEntry entry;
    fizz::detail::readBuf<uint32_t>(entry.cert_data, cursor);
    if (!entry.cert_data->empty()) {
      psk.serverCert = factory.makePeerCert(std::move(entry), true);
    }

    fizz::CertificateEntry clientEntry;
    fizz::detail::readBuf<uint32_t>(clientEntry.cert_data, cursor);
    if (!clientEntry.cert_data->empty()) {
      psk.clientCert = factory.makePeerCert(std::move(clientEntry), true);
    }

    fizz::detail::read(psk.maxEarlyDataSize, cursor);

    // if (!cursor.isAtEnd()) {
      uint64_t ticketHandshakeTime;
      fizz::detail::read(ticketHandshakeTime, cursor);
      LOG(INFO) << ticketHandshakeTime;
      psk.ticketHandshakeTime =
          std::chrono::time_point<std::chrono::system_clock>(
              std::chrono::milliseconds(ticketHandshakeTime));
    // } else {
    //   // Just assign it now();
    //   psk.ticketHandshakeTime = std::chrono::system_clock::now();
    //}

    qpsk.cachedPsk = psk;
  
    CachedServerTransportParameters transportParams;
    fizz::detail::read(transportParams.idleTimeout, cursor);
    fizz::detail::read(transportParams.maxRecvPacketSize, cursor);
    fizz::detail::read(transportParams.initialMaxData, cursor);
    fizz::detail::read(transportParams.initialMaxStreamDataBidiLocal, cursor);
    fizz::detail::read(transportParams.initialMaxStreamDataBidiRemote, cursor);
    fizz::detail::read(transportParams.initialMaxStreamDataUni, cursor);
    fizz::detail::read(transportParams.initialMaxStreamsBidi, cursor);
    fizz::detail::read(transportParams.initialMaxStreamsUni, cursor);
    qpsk.transportParams = transportParams;

    std::string appParams = "";
    std::unique_ptr<folly::IOBuf> appParamData;
    fizz::detail::readBuf<uint8_t>(appParamData, cursor);
    if (!appParamData->empty()) {
      appParams = appParamData->moveToFbString().toStdString();
    }
    qpsk.appParams = appParams;

    return qpsk;
  }


 private:
  std::string saveFile_, loadFile_;
};


class EchoClient : public quic::QuicSocket::ConnectionSetupCallback,
                   public quic::QuicSocket::ConnectionCallback,
                   public quic::QuicSocket::ReadCallback,
                   public quic::QuicSocket::WriteCallback,
                   public quic::QuicSocket::DatagramCallback {
 public:
  EchoClient(
      const std::string& host,
      uint16_t port,
      bool useDatagrams,
      uint64_t activeConnIdLimit,
      bool enableMigration,
      bool zrtt)
      : host_(host),
        port_(port),
        useDatagrams_(useDatagrams),
        activeConnIdLimit_(activeConnIdLimit),
        enableMigration_(enableMigration),
        zrtt_(zrtt) {}

  void readAvailable(quic::StreamId streamId) noexcept override {
    auto readData = quicClient_->read(streamId, 0);
    if (readData.hasError()) {
      LOG(ERROR) << "EchoClient failed read from stream=" << streamId
                 << ", error=" << (uint32_t)readData.error();
    }
    auto copy = readData->first->clone();
    if (recvOffsets_.find(streamId) == recvOffsets_.end()) {
      recvOffsets_[streamId] = copy->length();
    } else {
      recvOffsets_[streamId] += copy->length();
    }
    LOG(INFO) << "Client received data=" << copy->moveToFbString().toStdString()
              << " on stream=" << streamId;
  }

  void readError(quic::StreamId streamId, QuicError error) noexcept override {
    LOG(ERROR) << "EchoClient failed read from stream=" << streamId
               << ", error=" << toString(error);
    // A read error only terminates the ingress portion of the stream state.
    // Your application should probably terminate the egress portion via
    // resetStream
  }

  void onNewBidirectionalStream(quic::StreamId id) noexcept override {
    LOG(INFO) << "EchoClient: new bidirectional stream=" << id;
    quicClient_->setReadCallback(id, this);
  }

  void onNewUnidirectionalStream(quic::StreamId id) noexcept override {
    LOG(INFO) << "EchoClient: new unidirectional stream=" << id;
    quicClient_->setReadCallback(id, this);
  }

  void onStopSending(
      quic::StreamId id,
      quic::ApplicationErrorCode /*error*/) noexcept override {
    VLOG(10) << "EchoClient got StopSending stream id=" << id;
  }

  void onConnectionEnd() noexcept override {
    LOG(INFO) << "EchoClient connection end";
  }

  void onConnectionSetupError(QuicError error) noexcept override {
    onConnectionError(std::move(error));
  }

  void onConnectionError(QuicError error) noexcept override {
    LOG(ERROR) << "EchoClient error: " << toString(error.code)
               << "; errStr=" << error.message;
    startDone_.post();
  }

  void onTransportReady() noexcept override {
    startDone_.post();
  }

  void onStreamWriteReady(quic::StreamId id, uint64_t maxToSend) noexcept
      override {
    LOG(INFO) << "EchoClient socket is write ready with maxToSend="
              << maxToSend;
    sendMessage(id, pendingOutput_[id]);
  }

  void onStreamWriteError(quic::StreamId id, QuicError error) noexcept
      override {
    LOG(ERROR) << "EchoClient write error with stream=" << id
               << " error=" << toString(error);
  }

  void onDatagramsAvailable() noexcept override {
    auto res = quicClient_->readDatagrams();
    if (res.hasError()) {
      LOG(ERROR) << "EchoClient failed reading datagrams; error="
                 << res.error();
      return;
    }
    for (const auto& datagram : *res) {
      LOG(INFO) << "Client received datagram ="
                << datagram.bufQueue()
                       .front()
                       ->cloneCoalesced()
                       ->moveToFbString()
                       .toStdString();
    }
  }

  void start(std::string token) {
    folly::ScopedEventBaseThread networkThread("EchoClientThread");
    auto evb = networkThread.getEventBase();
    folly::SocketAddress addr(host_.c_str(), port_);

    auto pskSaveFile = std::string("/home/user/Documents/QUIC-RFC9000/ticket_mvfst.bin");
    auto pskLoadFile = std::string("/home/user/Documents/QUIC-RFC9000/ticket_mvfst.bin");
    if(const char* env_p = std::getenv("PROOTPATH")) {
       pskSaveFile = std::string(env_p) + std::string("/tickets/ticket_mvfst.bin");
       pskLoadFile = std::string(env_p) + std::string("/tickets/ticket_mvfst.bin");
    }
    auto pskCache_ =
          std::make_shared<BasicPersistentQuicPskCache>(pskSaveFile, pskLoadFile);
    auto clientCtx = std::make_shared<fizz::client::FizzClientContext>();
    evb->runInEventBaseThreadAndWait([&] {

      auto sock = std::make_unique<folly::AsyncUDPSocket>(evb);
      clientCtx->setSupportedAlpns({"hq"});
      clientCtx->setClock(std::make_shared<NiceMock<fizz::test::MockClock>>());

      auto fizzClientContext =
          FizzClientQuicHandshakeContext::Builder()
              .setFizzClientContext(clientCtx)
              .setCertificateVerifier(test::createTestCertificateVerifier())
              .setPskCache(pskCache_)
              .build();
      quicClient_ = std::make_shared<quic::QuicClientTransport>(
          evb, std::move(sock), std::move(fizzClientContext));
      auto hostname = "echo.com";
      quicClient_->setHostname(hostname);
      quicClient_->addNewPeerAddress(addr);
      if (!token.empty()) {
        quicClient_->setNewToken(token);
      }
      if (useDatagrams_) {
        auto res = quicClient_->setDatagramCallback(this);
        CHECK(res.hasValue()) << res.error();
      }

      TransportSettings settings;
      settings.datagramConfig.enabled = useDatagrams_;
      if(zrtt_) {
        settings.attemptEarlyData = true;
      }
      settings.selfActiveConnectionIdLimit = activeConnIdLimit_;
      settings.disableMigration = !enableMigration_;
      quicClient_->setTransportSettings(settings);
      if(zrtt_) {
        clientCtx->setSendEarlyData(true);
        auto cachedPsk = pskCache_->getPsk(hostname);
        //     setupZeroRttOnClientCtx(*clientCtx,hostname);
        if(cachedPsk) {
          pskCache_->putPsk(hostname, cachedPsk.value()); 
        }
      }

      quicClient_->setTransportStatsCallback(
          std::make_shared<LogQuicStats>("client"));

      LOG(INFO) << "EchoClient connecting to " << addr.describe();
      quicClient_->start(this, this);
    });

    startDone_.wait();

    std::string message;
    auto client = quicClient_;
    // loop until Ctrl+D
    while (std::getline(std::cin, message)) {
      if (message.empty()) {
        continue;
      }
      evb->runInEventBaseThreadAndWait([=] {
        // create new stream for each message
        auto streamId = client->createBidirectionalStream().value();
        client->setReadCallback(streamId, this);
        pendingOutput_[streamId].append(folly::IOBuf::copyBuffer(message));
        sendMessage(streamId, pendingOutput_[streamId]);
      });
    }
    LOG(INFO) << "EchoClient stopping client";
  }

  ~EchoClient() override = default;

 private:
  void sendMessage(quic::StreamId id, BufQueue& data) {
    auto message = data.move();
    auto res = useDatagrams_
        ? quicClient_->writeDatagram(message->clone())
        : quicClient_->writeChain(id, message->clone(), true);
    if (res.hasError()) {
      LOG(ERROR) << "EchoClient writeChain error=" << uint32_t(res.error());
    } else {
      auto str = message->moveToFbString().toStdString();
      LOG(INFO) << "EchoClient wrote \"" << str << "\""
                << ", len=" << str.size() << " on stream=" << id;
      // sent whole message
      pendingOutput_.erase(id);
    }
  }

  std::string host_;
  uint16_t port_;
  bool useDatagrams_;
  uint64_t activeConnIdLimit_;
  bool enableMigration_;
  bool zrtt_;
  std::shared_ptr<quic::QuicClientTransport> quicClient_;
  std::map<quic::StreamId, BufQueue> pendingOutput_;
  std::map<quic::StreamId, uint64_t> recvOffsets_;
  folly::fibers::Baton startDone_;
};
} // namespace samples
} // namespace quic
