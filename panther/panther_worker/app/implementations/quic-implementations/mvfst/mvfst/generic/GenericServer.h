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
#include <quic/samples/generic/GenericHandler.h>
#include <quic/samples/generic/LogQuicStats.h>
#include <quic/server/QuicServer.h>
#include <quic/server/QuicServerTransport.h>
#include <quic/server/QuicSharedUDPSocketFactory.h>

namespace quic {
namespace samples {

class GenericServerTransportFactory : public quic::QuicServerTransportFactory {
 public:
  ~GenericServerTransportFactory() override {
    while (!genericHandlers_.empty()) {
      auto& handler = genericHandlers_.back();
      handler->getEventBase()->runImmediatelyOrRunInEventBaseThreadAndWait(
          [this] {
            // The evb should be performing a sequential consistency atomic
            // operation already, so we can bank on that to make sure the writes
            // propagate to all threads.
            genericHandlers_.pop_back();
          });
    }
  }

  GenericServerTransportFactory(bool prEnabled = false, CongestionControlType cc = CongestionControlType::Cubic, std::shared_ptr<FileQLogger> qLogger = nullptr) : prEnabled_(prEnabled), cc_(cc), qLogger_(qLogger) {}

  quic::QuicServerTransport::Ptr make(
      folly::EventBase* evb,
      std::unique_ptr<folly::AsyncUDPSocket> sock,
      const folly::SocketAddress&,
      std::shared_ptr<const fizz::server::FizzServerContext>
          ctx) noexcept override {
    CHECK_EQ(evb, sock->getEventBase());
    auto genericHandler = std::make_unique<GenericHandler>(evb, prEnabled_);
    auto transport = quic::QuicServerTransport::make(
            evb, std::move(sock), *genericHandler, ctx);
    TransportSettings settings;
    settings.pacingEnabled = true;
    settings.defaultCongestionController = cc_;
    settings.maxCwndInMss = kLargeMaxCwndInMss;
    transport->setCongestionControllerFactory(
            std::make_shared<DefaultCongestionControllerFactory>());
    transport->setPacingTimer(TimerHighRes::newTimer(evb, transport->getTransportSettings().pacingTimerTickInterval));
    transport->setTransportSettings(settings);

    if (qLogger_ != nullptr) {
        transport->setQLogger(qLogger_);
    }

    genericHandler->setQuicSocket(transport);
    genericHandlers_.push_back(std::move(genericHandler));
    LOG(INFO) << "set congestion control " << congestionControlTypeToString(cc_);
    transport->setCongestionControl(cc_);
    LOG(INFO) << "hello";
    return transport;
  }

  std::vector<std::unique_ptr<GenericHandler>> genericHandlers_;

 private:
  bool prEnabled_;
  CongestionControlType cc_;
  std::shared_ptr<FileQLogger> qLogger_;
};

class GenericServer {
 public:
  explicit GenericServer(
      const std::string& host = "::",
      uint16_t port = 6666, CongestionControlType cc = CongestionControlType::BBR, std::shared_ptr<FileQLogger> qLogger = nullptr)
      : host_(host),
        port_(port),
        server_(QuicServer::createQuicServer()) {

    TransportSettings settings;
    settings.pacingEnabled = true;
    settings.defaultCongestionController = cc;
    settings.maxCwndInMss = kLargeMaxCwndInMss;
    server_->setTransportSettings(settings);

    server_->setQuicServerTransportFactory(
        std::make_unique<GenericServerTransportFactory>(prEnabled_, cc, qLogger));
    server_->setTransportStatsCallbackFactory(
        std::make_unique<LogQuicStatsFactory>());
    auto serverCtx = quic::test::createServerCtx();
    serverCtx->setClock(std::make_shared<fizz::SystemClock>());
    server_->setFizzContext(serverCtx);
  }

  void start() {
    // Create a SocketAddress and the default or passed in host.
    folly::SocketAddress addr1(host_.c_str(), port_);
    addr1.setFromHostPort(host_, port_);
    server_->start(addr1, 0);
    LOG(INFO) << "Generic server started at: " << addr1.describe();
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
