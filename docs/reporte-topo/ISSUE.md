<!--
  Texto listo para pegar como "New issue" en https://github.com/filirnd/topo/issues
  Título sugerido:
  Findings from a fork: newer C200 firmware needs the preview request, plus a few streaming/playback fixes
-->

Hi! First of all, thank you for Topo. The cloud login, request signing and relay work you did saved us a lot of time.

We built a Windows-focused fork on top of Topo 0.1.7 and tested it with 7 cameras: C200 on firmware 1.3.17 and 1.9.1, and C500 1.3.5. Along the way we found some issues that other Topo users may also hit. Here they are, in case they're useful. Feel free to use any of it.

## 1. Newer firmware sends no live video until the client asks for it

**Camera:** C200, firmware `1.3.17 Build 260112 Rel.58281n(4555)`. Another C200 on build `Rel.54862n` and C200 1.9.1 were not affected.

**Symptom:** `/v2/relay/request` succeeds and the relay answers `HTTP/1.1 200 OK` with `multipart/mixed`, but no part ever arrives and the read times out. The camera shows up in Topo only while the **official app is watching it at the same time**; then video starts flowing within about 3 seconds.

**Cause:** the official app sends a request over the client side of the multipart stream right after opening the relay. Older firmware streams without it; this one waits. The protocol is documented by [tothi/tapo-view](https://github.com/tothi/tapo-view).

**Fix:** right after sending the relay `POST`, send:

```
----client-stream-boundary--\r\n
Content-Type: application/json\r\n
Content-Length: <n>\r\n
X-Data-Window-Size: 50\r\n
\r\n
{"type":"request","seq":1,"params":{"method":"get","preview":{"channels":[0],"resolutions":["HD"],"audio":["default"]}}}\r\n
```

Then keep the session alive:
- **Ack every 25 parts:** `{"type":"notification","params":{"event_type":"stream_sequence"}}` with headers `X-Data-Received: <X-Data-Sequence of the part>` and `X-Session-Id: <session_id>`. The `session_id` comes in the camera's JSON response and in the `X-Session-Id` part header. Without acks, a window of 50 can stall the stream.
- **Heartbeat every 20 s:** `{"type":"notification","params":{"event_type":"heartbeat"}}`.

This also works with the older firmware we tested.

## 2. JSON parts from the camera are fed to FFmpeg as video

In `_relay_once`, every part with `length > 0` is treated as video. With the preview request, the camera also sends `application/json` parts (the response with `session_id`, and notifications such as `channel_motor_status` or `connection_closed`). We now check `Content-Type` and only pipe parts that aren't JSON.

## 3. A new viewer restarts the relay for everyone, and late joiners get a broken MP4

- `subscribe_native_video` calls `_interrupt_relay()` whenever the remuxer isn't running, and `subscribe_audio` does too for the first audio listener. Opening audio or a second tab cuts the video for everyone already watching.
- `_read_native_video` broadcasts raw 16 KB reads. A viewer that joins mid-stream gets the init segment followed by bytes from the **middle of a box**. The browser fails, reconnects, and with the point above that turns into a reconnect loop. In our logs one camera reconnected 4 times in 2 minutes.

**Fix:** parse the remuxer output into whole boxes and broadcast complete `moof+mdat` fragments. Keep the init segment and a cache from the last keyframe; the sync flag is in `trun` `first_sample_flags` or the `tfhd` default flags, bit `0x00010000` = non-sync. A new viewer gets init + cached fragments and plays immediately, without touching the relay. Audio starts its encoder inside the running relay instead of restarting it.

## 4. Smaller things

- **Idle relays never close:** once a camera has been watched, its relay and FFmpeg keep running even with no viewers. We close the relay after 20 s without subscribers.
- **Unbounded subscriber queues:** a slow viewer makes its queue grow without limit. We disconnect a viewer that falls more than about 90 fragments behind, and it reconnects at the live edge.
- **Many cameras on HTTP/1.1:** the browser opens at most 6 connections per host, so a grid of 7 endless streams starves the rest of the page. One stream at a time, or only visible cameras, avoids it.

## 5. SD recordings

- **`searchVideoOfDay` with `end_index: 999999999` returns `{"outputParams":{}}`** on days with many clips (C200 1.3.17, about 280 clips per day). The same call with `start_index: 0, end_index: 49` works. We paginate in pages of 50 until a page returns fewer than 50. Passing `id` as a string, or omitting it, returns `-71112`.
- **Playback while a live relay is open** fails at the relay with `500 {"errorCode":-52207,"closeReason":"passthrough fail"}`. The camera can't serve live and playback at the same time. Closing the live relay first, waiting about 2.5 s and retrying fixes it.
- **Playback also needs acks** (`stream_sequence`, window 40), or long clips stall.
- **Open question:** on C200 `1.3.17 Build 260112 Rel.58281n` the playback request always returns `{"type":"response","params":{"error_code":-52402}}`. We tried `seq` 1 vs 1000+, `channels` `[0,1]` vs `[0]`, numeric vs string times, without `event_type`/`scale`, and `X-Client-Model` set to the camera model without `X-Compete`. The exact same request works on C200 1.9.1. If you ever find what the official app sends for that firmware, we'd love to know.

Thanks again for publishing Topo under MIT!
