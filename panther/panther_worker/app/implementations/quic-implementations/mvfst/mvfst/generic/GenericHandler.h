/*
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 *
 */

#pragma once

#include <quic/api/QuicSocket.h>

#include <folly/io/async/EventBase.h>
#include <quic/common/BufUtil.h>

namespace quic {
namespace samples {
class GenericHandler : public quic::QuicSocket::ConnectionCallback,
                       public quic::QuicSocket::ReadCallback,
                       public quic::QuicSocket::WriteCallback {
 public:
  using StreamData = std::pair<BufQueue, bool>;

  explicit GenericHandler(folly::EventBase* evbIn, bool prEnabled = false)
      : evb(evbIn) {}

  void setQuicSocket(std::shared_ptr<quic::QuicSocket> socket) {
    sock = socket;
  }

  void onNewBidirectionalStream(quic::StreamId id) noexcept override {
    LOG(INFO) << "Got bidirectional stream id=" << id;
    sock->setReadCallback(id, this);
  }

  void onNewUnidirectionalStream(quic::StreamId id) noexcept override {
    LOG(INFO) << "Got unidirectional stream id=" << id;
    sock->setReadCallback(id, this);
  }

  void onStopSending(
      quic::StreamId id,
      quic::ApplicationErrorCode error) noexcept override {
    LOG(INFO) << "Got StopSending stream id=" << id << " error=" << error;
  }

  void onConnectionEnd() noexcept override {
    LOG(INFO) << "Socket closed";
  }

  void onConnectionError(
      std::pair<quic::QuicErrorCode, std::string> error) noexcept override {
    LOG(ERROR) << "Socket error=" << toString(error.first);
  }

  void readAvailable(quic::StreamId id) noexcept override {
    LOG(INFO) << "read available for stream id=" << id;

    auto res = sock->read(id, 0);
    if (res.hasError()) {
      LOG(ERROR) << "Got error=" << toString(res.error());
      return;
    }
    if (input_.find(id) == input_.end()) {
      input_.emplace(id, std::make_pair(BufQueue(), false));
    }
    quic::Buf data = std::move(res.value().first);
    bool eof = res.value().second;
    auto dataLen = (data ? data->computeChainDataLength() : 0);
    std::string data_str = (data) ? data->clone()->moveToFbString().toStdString() : std::string();
    LOG(INFO) << "Got len=" << dataLen << " eof=" << uint32_t(eof)
              << " total=" << input_[id].first.chainLength() + dataLen
              << " data="
              << (data_str);
    input_[id].first.append(std::move(data));
    input_[id].second = eof;
    if (eof) {
        if (dataLen == 0) {
            return;
        }
//        char *str = (char *) calloc(1,  request_len + 1);
//        if (!str) {
//            LOG(ERROR) << "OUT OF MEMORY";
//            return;
//        }

        if (data_str[0] != '/') {
            LOG(ERROR) << "BAD REQUEST";
        } else {
            data_str.erase(0, 1); // remove the leading /
            long int requested_size = std::stol(data_str);
            LOG(INFO) << "PROCESSING REQUEST, SIZE = " << requested_size;
            serve(id, requested_size);
        }
//        free(str);
    }
  }

  void readError(
      quic::StreamId id,
      std::pair<quic::QuicErrorCode, folly::Optional<folly::StringPiece>>
          error) noexcept override {
    LOG(WARNING) << "Got read error on stream=" << id
               << " error=" << toString(error);
    // A read error only terminates the ingress portion of the stream state.
    // Your application should probably terminate the egress portion via
    // resetStream
  }

  void serve(quic::StreamId id, size_t size) {
    uint8_t *data = (uint8_t *) malloc(size);
    auto response = folly::IOBuf::wrapBuffer(data, size);
//    auto echoedData = folly::IOBuf::copyBuffer("echo ");

//    echoedData->prependChain(data.first.move());
    auto res =
        sock->writeChain(id, std::move(response), true, false, nullptr);
    if (res.hasError()) {
      LOG(ERROR) << "write error=" << toString(res.error());
    }
  }


  void onStreamWriteReady(
      quic::StreamId id,
      uint64_t maxToSend) noexcept override {
    LOG(INFO) << "socket is write ready with maxToSend=" << maxToSend;
    LOG(ERROR) << "SHOULD NOT HAPPEN";
  }

  void onStreamWriteError(
      quic::StreamId id,
      std::pair<quic::QuicErrorCode, folly::Optional<folly::StringPiece>>
          error) noexcept override {
    LOG(ERROR) << "write error with stream=" << id
               << " error=" << toString(error);
  }

  folly::EventBase* getEventBase() {
    return evb;
  }

  folly::EventBase* evb;
  std::shared_ptr<quic::QuicSocket> sock;

 private:
  std::map<quic::StreamId, StreamData> input_;
};
} // namespace samples
} // namespace quic
