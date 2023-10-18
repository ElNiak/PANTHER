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
#include <fizz/crypto/aead/test/Mocks.h>
#include <fizz/protocol/clock/test/Mocks.h>
#include <quic/api/QuicSocket.h>
#include <quic/client/QuicClientTransport.h>
#include <quic/common/BufUtil.h>
#include <quic/common/test/TestUtils.h>
#include <quic/fizz/client/handshake/FizzClientQuicHandshakeContext.h>
#include <quic/samples/echo/LogQuicStats.h>

namespace quic {
namespace samples {
class EchoClient : public quic::QuicSocket::ConnectionCallback,
                   public quic::QuicSocket::ReadCallback,
                   public quic::QuicSocket::WriteCallback,
                   public quic::QuicSocket::DataExpiredCallback {
 public:
  EchoClient(const std::string& host, uint16_t port, bool prEnabled = false,  bool zrtt = false)
      : host_(host), port_(port), prEnabled_(prEnabled), zrtt_(zrtt) {}

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

  void readError(
      quic::StreamId streamId,
      std::pair<quic::QuicErrorCode, folly::Optional<folly::StringPiece>>
          error) noexcept override {
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

  void onConnectionError(
      std::pair<quic::QuicErrorCode, std::string> error) noexcept override {
    LOG(ERROR) << "EchoClient error: " << toString(error.first);
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

  void onStreamWriteError(
      quic::StreamId id,
      std::pair<quic::QuicErrorCode, folly::Optional<folly::StringPiece>>
          error) noexcept override {
    LOG(ERROR) << "EchoClient write error with stream=" << id
               << " error=" << toString(error);
  }

  void onDataExpired(StreamId streamId, uint64_t newOffset) noexcept override {
    LOG(INFO) << "Client received skipData; "
              << newOffset - recvOffsets_[streamId]
              << " bytes skipped on stream=" << streamId;
  }

  void start() {
    folly::ScopedEventBaseThread networkThread("EchoClientThread");
    auto evb = networkThread.getEventBase();
    folly::SocketAddress addr(host_.c_str(), port_);

    std::shared_ptr<QuicPskCache> pskCache_;
    pskCache_ = std::make_shared<BasicQuicPskCache>();
    auto clientCtx = std::make_shared<fizz::client::FizzClientContext>();

    evb->runInEventBaseThreadAndWait([&] {
      auto sock = std::make_unique<folly::AsyncUDPSocket>(evb);

      clientCtx->setSupportedAlpns({"hq-29"});
      clientCtx->setClock(std::make_shared<NiceMock<fizz::test::MockClock>>());

      // auto serverCtx = test::createServerCtx();
      // serverCtx->setSupportedAlpns({"h1q-fb", "hq"});

      auto fizzClientContext =
          FizzClientQuicHandshakeContext::Builder()
              .setFizzClientContext(clientCtx)
              .setCertificateVerifier(test::createTestCertificateVerifier())
              .setPskCache(pskCache_)
              .build();
      quicClient_ = std::make_shared<quic::QuicClientTransport>(
          evb, 
          std::move(sock), 
          std::move(fizzClientContext));
      std::string hostname = "servername"; 
      quicClient_->setHostname(hostname);
      quicClient_->addNewPeerAddress(addr);

      TransportSettings settings;
      if (prEnabled_) {
        settings.partialReliabilityEnabled = true;
      }
      if(zrtt_) {
        settings.attemptEarlyData = true;
      }
      quicClient_->setTransportSettings(settings);

      auto cachedPsk =
          test::setupZeroRttOnClientCtx(*clientCtx,hostname); 
      pskCache_->putPsk(hostname, cachedPsk); 

      // folly::Optional<std::string> alpn = std::string("hq-29");
      // bool performedValidation = false;
      // quicClient_->setEarlyDataAppParamsFunctions(
      //     [&](const folly::Optional<std::string>& alpnToValidate, const Buf&) {
      //       performedValidation = true;
      //       EXPECT_EQ(alpnToValidate, alpn);
      //       return true;
      //     },
      //     []() -> Buf { return nullptr; });

      quicClient_->setTransportStatsCallback(
          std::make_shared<LogQuicStats>("client"));

      // test::setupZeroRttOnServerCtx(*serverCtx, cachedPsk);

      
      LOG(INFO) << "EchoClient connecting to " << addr.describe();
      //quicClient_->getConn().zeroRttWriteCipher;
      quicClient_->start(this);
    });

    startDone_.wait();

    std::string message;
    // create new stream for each message
    auto streamId = quicClient_->createBidirectionalStream().value();
    quicClient_->setReadCallback(streamId, this);
    pendingOutput_[streamId].append(folly::IOBuf::copyBuffer("/​​​​​​​50000"));
    sendMessage(streamId, pendingOutput_[streamId]);
    gettimeofday(&requestTime, NULL);

    transferDone_.wait();
    quicClient_->closeGracefully();
    quicClient_->closeTransport();
    std::pair p(QuicErrorCode(TransportErrorCode::NO_ERROR), std::string("No error"));
    quicClient_->closeNow(p);

    // loop until Ctrl+D
    /*
    while (std::getline(std::cin, message)) {
        if (message.empty()) {
          continue;
        }
        evb->runInEventBaseThreadAndWait([=] {
          // create new stream for each message
          auto streamId = client->createBidirectionalStream().value();
          client->setReadCallback(streamId, this);
          if (prEnabled_) {
            client->setDataExpiredCallback(streamId, this);
          }
          pendingOutput_[streamId].append(folly::IOBuf::copyBuffer(message));
          sendMessage(streamId, pendingOutput_[streamId]);
        });
      }
      */
    LOG(INFO) << "EchoClient stopping client";
  }

  ~EchoClient() override = default;

 private:
  void sendMessage(quic::StreamId id, BufQueue& data) {
    auto message = data.move();
    auto res = quicClient_->writeChain(id, message->clone(), true, false);
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

  size_t requestedSize_;
  size_t window_;

  folly::fibers::Baton transferDone_;
  folly::fibers::Baton connectionEnd_;

  std::string host_;
  uint16_t port_;
  bool prEnabled_;
  bool zrtt_;
  struct timeval requestTime;
  std::shared_ptr<quic::QuicClientTransport> quicClient_;
  std::map<quic::StreamId, BufQueue> pendingOutput_;
  std::map<quic::StreamId, uint64_t> recvOffsets_;
  folly::fibers::Baton startDone_;
};
} // namespace samples
} // namespace quic
