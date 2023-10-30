/*
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 *
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
#include <quic/common/test/TestUtils.h>
#include <quic/fizz/client/handshake/FizzClientQuicHandshakeContext.h>
#include <quic/samples/generic/LogQuicStats.h>

namespace quic {
namespace samples {
class GenericClient : public quic::QuicSocket::ConnectionCallback,
                      public quic::QuicSocket::ReadCallback,
                      public quic::QuicSocket::WriteCallback,
                      public quic::QuicSocket::DataExpiredCallback {
 public:
  GenericClient(const std::string& host, uint16_t port, size_t requested_size, size_t window)
      : host_(host), port_(port), requestedSize_(requested_size), window_(window) {}

  void readAvailable(quic::StreamId streamId) noexcept override {
    auto readData = quicClient_->read(streamId, 0);
    if (readData.hasError()) {
      LOG(ERROR) << "GenericClient failed read from stream=" << streamId
                 << ", error=" << (uint32_t)readData.error();
    }
    auto copy = readData->first->clone();
    if (recvOffsets_.find(streamId) == recvOffsets_.end()) {
        recvOffsets_[streamId] = copy->length();
    } else {
        recvOffsets_[streamId] += copy->length();
    }
    if (readData->second) {
        LOG(INFO) << "FIN RECEIVED";
        struct timeval now;
        gettimeofday(&now, NULL);
        double delta = (now.tv_sec - requestTime.tv_sec) * 1000.0 + (((double)(now.tv_usec - requestTime.tv_usec))/1000.0);
        LOG(INFO) << "RECEIVED " << recvOffsets_[streamId] << "bytes";
        printf("%.3f ms\ndone\n", delta);
        transferDone_.post();
    }
//    LOG(INFO) << "Client received data=" << copy->moveToFbString().toStdString()
//              << " on stream=" << streamId;
  }

  void readError(
      quic::StreamId streamId,
      std::pair<quic::QuicErrorCode, folly::Optional<folly::StringPiece>>
          error) noexcept override {
    LOG(ERROR) << "GenericClient failed read from stream=" << streamId
               << ", error=" << toString(error);
    // A read error only terminates the ingress portion of the stream state.
    // Your application should probably terminate the egress portion via
    // resetStream
  }

  void onNewBidirectionalStream(quic::StreamId id) noexcept override {
    LOG(INFO) << "GenericClient: new bidirectional stream=" << id;
    quicClient_->setReadCallback(id, this);
  }

  void onNewUnidirectionalStream(quic::StreamId id) noexcept override {
    LOG(INFO) << "GenericClient: new unidirectional stream=" << id;
    quicClient_->setReadCallback(id, this);
  }

  void onStopSending(
      quic::StreamId id,
      quic::ApplicationErrorCode /*error*/) noexcept override {
    VLOG(10) << "GenericClient got StopSending stream id=" << id;
  }

  void onConnectionEnd() noexcept override {
    LOG(INFO) << "GenericClient connection end";
    connectionEnd_.post();
  }

  void onConnectionError(
      std::pair<quic::QuicErrorCode, std::string> error) noexcept override {
    LOG(ERROR) << "GenericClient error: " << toString(error.first);
    startDone_.post();
  }

  void onTransportReady() noexcept override {
    startDone_.post();
  }

  void onStreamWriteReady(
      quic::StreamId id,
      uint64_t maxToSend) noexcept override {
    LOG(INFO) << "GenericClient socket is write ready with maxToSend="
              << maxToSend;
    sendMessage(id, pendingOutput_[id]);
  }

  void onStreamWriteError(
      quic::StreamId id,
      std::pair<quic::QuicErrorCode, folly::Optional<folly::StringPiece>>
          error) noexcept override {
    LOG(ERROR) << "GenericClient write error with stream=" << id
               << " error=" << toString(error);
  }

  void onDataExpired(StreamId streamId, uint64_t newOffset) noexcept override {
    LOG(INFO) << "Client received skipData; "
              << newOffset - recvOffsets_[streamId]
              << " bytes skipped on stream=" << streamId;
  }

  void start(CongestionControlType cc) {
    folly::ScopedEventBaseThread networkThread("GenericClientThread");
    auto evb = networkThread.getEventBase();
    folly::SocketAddress addr(host_.c_str(), port_);

    evb->runInEventBaseThreadAndWait([&] {
      auto sock = std::make_unique<folly::AsyncUDPSocket>(evb);
      auto fizzClientContext =
          FizzClientQuicHandshakeContext::Builder()
              .setCertificateVerifier(test::createTestCertificateVerifier())
              .build();
      quicClient_ = std::make_shared<quic::QuicClientTransport>(
          evb, std::move(sock), std::move(fizzClientContext));

      // force draft 29
      quicClient_->setSupportedVersions({QuicVersion::QUIC_DRAFT});

      quicClient_->setCongestionControllerFactory(
              std::make_shared<DefaultCongestionControllerFactory>());
      TransportSettings settings;

      // window settings
      settings.advertisedInitialBidiLocalStreamWindowSize = window_;
      settings.advertisedInitialBidiRemoteStreamWindowSize = window_;
      settings.advertisedInitialConnectionWindowSize = window_;
      settings.advertisedInitialUniStreamWindowSize = window_;

      settings.pacingEnabled = true;
      settings.defaultCongestionController = cc;
      quicClient_->setPacingTimer(TimerHighRes::newTimer(evb, settings.pacingTimerTickInterval));
      quicClient_->setTransportSettings(settings);
      quicClient_->setCongestionControl(cc);
      LOG(INFO) << "set congestion control " << congestionControlTypeToString(cc);
      quicClient_->setHostname("generic.com");
      quicClient_->addNewPeerAddress(addr);

      quicClient_->setTransportStatsCallback(
          std::make_shared<LogQuicStats>("client"));

      LOG(INFO) << "GenericClient connecting to " << addr.describe();
      quicClient_->start(this);
    });

    startDone_.wait();

    std::string message;
    auto client = quicClient_;

    // create new stream for each message
    auto streamId = client->createBidirectionalStream().value();
    client->setReadCallback(streamId, this);
    pendingOutput_[streamId].append(folly::IOBuf::copyBuffer(fmt::format("/{}", requestedSize_)));
    sendMessage(streamId, pendingOutput_[streamId]);
    gettimeofday(&requestTime, NULL);

    transferDone_.wait();
    quicClient_->closeGracefully();
    quicClient_->closeTransport();
    std::pair p(QuicErrorCode(TransportErrorCode::NO_ERROR),
                std::string("No error"));
    quicClient_->closeNow(p);

//    // loop until Ctrl+D
//    while (std::getline(std::cin, message)) {
//      if (message.empty()) {
//        continue;
//      }
//      evb->runInEventBaseThreadAndWait([=] {
//        // create new stream for each message
//        auto streamId = client->createBidirectionalStream().value();
//        client->setReadCallback(streamId, this);
//        pendingOutput_[streamId].append(folly::IOBuf::copyBuffer(message));
//        sendMessage(streamId, pendingOutput_[streamId]);
//      });
//    }
  }

  ~GenericClient() override = default;

 private:
  void sendMessage(quic::StreamId id, BufQueue& data) {
    auto message = data.move();
    auto res = quicClient_->writeChain(id, message->clone(), true, false);
    if (res.hasError()) {
      LOG(ERROR) << "GenericClient writeChain error=" << uint32_t(res.error());
    } else {
//      auto str = message->moveToFbString().toStdString();
//      LOG(INFO) << "GenericClient wrote \"" << str << "\""
//                << ", len=" << str.size() << " on stream=" << id;
//      // sent whole message
      pendingOutput_.erase(id);
    }
  }


  std::string host_;
  uint16_t port_;
  size_t requestedSize_;
  size_t window_;
  struct timeval requestTime;
  std::shared_ptr<quic::QuicClientTransport> quicClient_;
  std::map<quic::StreamId, BufQueue> pendingOutput_;
  std::map<quic::StreamId, uint64_t> recvOffsets_;
  folly::fibers::Baton startDone_;
  folly::fibers::Baton transferDone_;
  folly::fibers::Baton connectionEnd_;
};
} // namespace samples
} // namespace quic
