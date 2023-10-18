/*
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

#include <quic/state/DatagramHandlers.h>

namespace quic {

void handleDatagram(
    QuicConnectionStateBase& conn,
    DatagramFrame& frame,
    TimePoint recvTimePoint) {
  // TODO(lniccolini) update max datagram frame size
  // https://github.com/quicwg/datagram/issues/3
  // For now, max_datagram_size > 0 means the peer supports datagram frames
  if (conn.datagramState.maxReadFrameSize == 0) {
    frame.data.move();
    QUIC_STATS(conn.statsCallback, onDatagramDroppedOnRead);
    return;
  }
  if (conn.datagramState.readBuffer.size() >=
      conn.datagramState.maxReadBufferSize) {
    QUIC_STATS(conn.statsCallback, onDatagramDroppedOnRead);
    if (!conn.transportSettings.datagramConfig.recvDropOldDataFirst) {
      frame.data.move();
      return;
    } else {
      conn.datagramState.readBuffer.pop_front();
    }
  }
  QUIC_STATS(conn.statsCallback, onDatagramRead, frame.data.chainLength());
  conn.datagramState.readBuffer.emplace_back(
      recvTimePoint, std::move(frame.data));
}

} // namespace quic
