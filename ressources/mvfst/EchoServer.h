/*
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 *
 */

#pragma once

#include <glog/logging.h>

#include <quic/common/test/TestUtils.h>
#include <quic/samples/echo/EchoHandler.h>
#include <quic/samples/echo/LogQuicStats.h>
#include <quic/server/QuicServer.h>
#include <quic/server/QuicServerTransport.h>
#include <quic/server/QuicSharedUDPSocketFactory.h>
#include <fizz/crypto/aead/AESGCM128.h>
#include <fizz/crypto/aead/OpenSSLEVPCipher.h>

#include <fizz/client/AsyncFizzClient.h>
#include <fizz/crypto/Utils.h>
#include <fizz/crypto/aead/AESGCM128.h>
#include <fizz/crypto/aead/OpenSSLEVPCipher.h>
#include <fizz/server/AsyncFizzServer.h>
#include <fizz/server/TicketTypes.h>
#include <folly/String.h>
#include <folly/io/async/AsyncSSLSocket.h>
#include <folly/io/async/SSLContext.h>
#include <folly/portability/GFlags.h>
#include <fizz/server/SlidingBloomReplayCache.h>

using namespace fizz;
using namespace fizz::client;
using namespace fizz::server;
using namespace folly;
using namespace folly::ssl;

namespace quic {
namespace samples {

class EchoServerTransportFactory : public quic::QuicServerTransportFactory {
 public:
  ~EchoServerTransportFactory() override {
    while (!echoHandlers_.empty()) {
      auto& handler = echoHandlers_.back();
      handler->getEventBase()->runImmediatelyOrRunInEventBaseThreadAndWait(
          [this] {
            // The evb should be performing a sequential consistency atomic
            // operation already, so we can bank on that to make sure the writes
            // propagate to all threads.
            echoHandlers_.pop_back();
          });
    }
  }

  EchoServerTransportFactory(bool prEnabled = false) : prEnabled_(prEnabled) {}

  quic::QuicServerTransport::Ptr make(
      folly::EventBase* evb,
      std::unique_ptr<folly::AsyncUDPSocket> sock,
      const folly::SocketAddress&,
      std::shared_ptr<const fizz::server::FizzServerContext>
          ctx) noexcept override {
    CHECK_EQ(evb, sock->getEventBase());
    auto echoHandler = std::make_unique<EchoHandler>(evb, prEnabled_);
    auto transport = quic::QuicServerTransport::make(
        evb, std::move(sock), *echoHandler, ctx);
    echoHandler->setQuicSocket(transport);
    echoHandlers_.push_back(std::move(echoHandler));
    return transport;
  }

  std::vector<std::unique_ptr<EchoHandler>> echoHandlers_;

 private:
  bool prEnabled_;
};

class EchoServer {
 public:
  explicit EchoServer(
      const std::string& host = "::1",
      uint16_t port = 6666,
      bool prEnabled = false)
      : host_(host),
        port_(port),
        prEnabled_(prEnabled),
        server_(QuicServer::createQuicServer()) {
    server_->setQuicServerTransportFactory(
        std::make_unique<EchoServerTransportFactory>(prEnabled_));
    server_->setTransportStatsCallbackFactory(
        std::make_unique<LogQuicStatsFactory>());
    auto serverCtx = quic::test::createServerCtx();
    serverCtx->setClock(std::make_shared<fizz::SystemClock>());
    
    serverCtx->setSendNewSessionTicket(true);
    auto ticketCipher = std::make_shared<AES128TicketCipher>();
    auto ticketSeed = RandomGenerator<32>().generateRandom();
    ticketCipher->setTicketSecrets({{range(ticketSeed)}});
    server::TicketPolicy policy;
    policy.setTicketValidity(std::chrono::seconds(5000));
    ticketCipher->setPolicy(std::move(policy));
    serverCtx->setTicketCipher(ticketCipher);

    serverCtx->setEarlyDataSettings(
          true,
          {std::chrono::seconds(-10), std::chrono::seconds(10)},
          std::make_shared<AllowAllReplayReplayCache>());
    serverCtx->setMaxEarlyDataSize(4294967295);
    
    server_->setFizzContext(serverCtx);
    if (prEnabled_) {
      TransportSettings settings;
      settings.partialReliabilityEnabled = true;
      server_->setTransportSettings(settings);
    }
  }

  void start() {
    // Create a SocketAddress and the default or passed in host.
    folly::SocketAddress addr1(host_.c_str(), port_);
    addr1.setFromHostPort(host_, port_);
    server_->start(addr1, 0);
    LOG(INFO) << "Echo server started at: " << addr1.describe();
    eventbase_.loopForever();
  }

 private:
  std::string host_;
  uint16_t port_;
  bool prEnabled_;
  folly::EventBase eventbase_;
  std::shared_ptr<quic::QuicServer> server_;
};
} // namespace samples
} // namespace quic
