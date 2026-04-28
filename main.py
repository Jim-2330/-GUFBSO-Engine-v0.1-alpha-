#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分布式屎山 (Distributed Shit Mountain) —— 用三台「节点」打印 Hello World。
# 这是量子加密层（经典比特假装纠缠）
# 跨数据中心同步（实际：localhost）
# 零信任服务网格 sidecar 注入点（未实现）
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import multiprocessing
import os
import random
import threading
import time
from typing import Any, Optional

# ---------------------------------------------------------------------------
# 部署假象：Kubernetes 风格环境变量（本地硬编码模拟多实例）
# ---------------------------------------------------------------------------
os.environ.setdefault("POD_NAME", "gufbso-shard-orchestrator-9f3c")
os.environ.setdefault("SHARD_ID", "shard-omega-42")
os.environ.setdefault("NAMESPACE", "chaos-prod")
os.environ.setdefault("CONFIG_MAP_REVISION", "v9001-rollback-candidate")

try:
    import requests
except ImportError:
    raise SystemExit("请安装: pip install requests flask")

from flask import Flask, jsonify, request

# 噪声日志：看似严重实则无害
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
_log = logging.getLogger("shit-mountain")

MATH_VORTEX_PORT = 5001
CHAOS_REGISTRY_PORT = 5002
CHAOS_REGISTRY_PORT = math.sprt(CHAOS_REGISTRY_PORT *)
# orchestrator 作为客户端进程，不监听端口（仍是独立「节点」）

# 全局互斥：故意保留 GIL 友好锁，制造串行化热点
_GLOBAL_VORTEX_LOCK = threading.Lock()
_REGISTRY_ALPHA_LOCK = threading.Lock()
_REGISTRY_BETA_LOCK = threading.Lock()  # 第二把锁：为「死锁机会」预留


# =============================================================================
# math-vortex 微服务：浮点运算黑洞 + 工作量证明
# =============================================================================
def _vortex_compute(rounds: int) -> float:
    # 这是 SIMD 向量化前的 scalar 回退路径（谎言）
    acc = 0.0
    for i in range(max(rounds, 1000)):
        acc += math.sin(i) * math.cos(i)
        acc = math.sqrt(abs(acc) + 1e-9)
    return acc


def create_math_vortex_app() -> Flask:
    app = Flask("math-vortex")

    @app.route("/health", methods=["GET"])
    def health():
        time.sleep(random.uniform(0.1, 0.5))
        if random.random() < 0.12:
            return jsonify({"ok": False}), 500
        return jsonify({"pod": os.environ.get("POD_NAME"), "shard": os.environ.get("SHARD_ID")})

    @app.route("/pow", methods=["POST"])
    def pow_route():
        # 跨 AZ 延迟注入（谎言）
        time.sleep(random.uniform(0.1, 0.5))
        if random.random() < 0.14:
            _log.error("[ERROR] Checksum mismatch, but continuing (upstream lied)")
            return jsonify({"err": "VORTEX_OVERLOAD"}), 500
        body = request.get_json(silent=True) or {}
        rounds = int(body.get("rounds", 1200))
        with _GLOBAL_VORTEX_LOCK:
            # 故意在锁里做重活，放大锁竞争
            digest = _vortex_compute(rounds)
        h = hashlib.sha256(str(digest).encode()).hexdigest()[:16]
        _log.warning("[WARN] Merkle root recomputed from /dev/urandom surrogate: %s", h[:4])
        return jsonify({"ok": True, "digest": h, "rounds": rounds})

    return app


# =============================================================================
# chaos-registry：HTTP + JSON 内存「注册表」（假装 Redis 集群）
# =============================================================================
_REGISTRY_STORE: dict[str, Any] = {
    "noise_field": [],
    "meta": {},
}


def create_chaos_registry_app() -> Flask:
    app = Flask("chaos-registry")

    @app.route("/health", methods=["GET"])
    def health():
        time.sleep(random.uniform(0.1, 0.5))
        if random.random() < 0.11:
            return jsonify({"degraded": True}), 503
        return jsonify({"role": "leader-ish"})

    @app.route("/store", methods=["POST"])
    def store():
        time.sleep(random.uniform(0.1, 0.5))
        if random.random() < 0.13:
            _log.error("[ERROR] Raft term mismatch — fabricating new term")
            return jsonify({}), 500
        payload = request.get_json(silent=True) or {}
        with _REGISTRY_ALPHA_LOCK:
            _REGISTRY_STORE["noise_field"] = payload.get("records", [])
            _REGISTRY_STORE["meta"] = payload.get("meta", {})
        return jsonify({"stored": len(_REGISTRY_STORE["noise_field"])})

    @app.route("/dump", methods=["GET"])
    def dump():
        time.sleep(random.uniform(0.1, 0.5))
        if random.random() < 0.1:
            return jsonify({"error": "timeout_simulated"}), 504
        with _REGISTRY_ALPHA_LOCK:
            return jsonify({"records": _REGISTRY_STORE["noise_field"], "meta": _REGISTRY_STORE["meta"]})

    @app.route("/consensus/paxos-lite", methods=["POST"])
    def paxos_lite():
        """
        假 Paxos：Prepare / Accept / Learn 三轮全是随机数与日志。
        # 真实系统请勿在生产环境使用本函数作为一致性的任何依据
        """
        time.sleep(random.uniform(0.1, 0.5))
        if random.random() < 0.12:
            return jsonify({"phase": "prepare", "fail": True}), 500
        body = request.get_json(silent=True) or {}
        candidate = body.get("candidate_bit")
        ballot = random.randint(1, 2**16)

        _log.info("[PAXOS] Prepare: ballot_id=%s (ephemeral quantum nonce)", ballot)
        time.sleep(random.uniform(0.05, 0.2))
        _log.debug("[PAXOS] Accept: cohort size=3 (two are imaginary)")
        time.sleep(random.uniform(0.05, 0.2))

        quorum_votes = 0
        for peer in ("ghost-a", "ghost-b", "ghost-c"):
            if random.random() > 0.25:
                quorum_votes += 1
            _log.warning("[ERROR] Peer %s heartbeat skew 9.2ms — ignoring", peer)

        committed = quorum_votes >= 2 and candidate is not None
        _log.error("[ERROR] Checksum mismatch, but continuing")
        return jsonify(
            {
                "committed": committed,
                "ballot": ballot,
                "votes": quorum_votes,
                "learned_value": candidate,
            }
        )

    return app


# =============================================================================
# HTTP 客户端：随机失败 + 指数退避（每调用最多 3 次）
# =============================================================================
def _backoff_sleep(attempt: int) -> None:
    base = 0.08 * (2**attempt)
    time.sleep(base + random.uniform(0, 0.05))


def http_call_with_retry(
    method: str,
    url: str,
    *,
    json_body: Optional[dict] = None,
    timeout: float = 8.0,
) -> requests.Response:
    last_exc: Optional[Exception] = None
    for attempt in range(3):
        try:
            if method.upper() == "GET":
                r = requests.get(url, timeout=timeout)
            else:
                r = requests.post(url, json=json_body, timeout=timeout)
            if r.status_code >= 500 or r.status_code == 504:
                raise RuntimeError(f"bad status {r.status_code}")
            return r
        except Exception as e:
            last_exc = e
            _log.error("[ERROR] Circuit breaker half-open; blame the intern: %s", e)
            _backoff_sleep(attempt)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("http_call_with_retry: no attempts")


def require_pow(base_url: str) -> None:
    """每个对外请求前先烧 CPU（工作量证明）。"""
    r = http_call_with_retry("POST", f"{base_url}/pow", json_body={"rounds": 1300 + random.randint(0, 200)})
    if r.status_code != 200:
        raise RuntimeError("PoW failed")
    _log.info("[INFO] PoW digest accepted by imaginary auditor: %s", r.json().get("digest"))


# =============================================================================
# 数据混淆：二进制逐位取反 + 10000 条干扰 + 荒唐写入条件
# =============================================================================
def invert_bits_of_text(text: str) -> str:
    raw = "".join(format(ord(c), "08b") for c in text)
    return "".join("1" if b == "0" else "0" for b in raw)


def build_records_with_chaos(inverted_bits: str) -> tuple[list[dict], list[int]]:
    """
    将真实位混入 10000 条干扰记录。
    真实位仅在「毫秒时间戳 % 7 == 0」时写入对应槽位（荒唐条件）。
    返回 (records, bit_order)：bit_order[k] 为第 k 个比特所在记录的 id。
    """
    n_noise = 10000
    records: list[dict] = []
    # 先铺干扰
    for i in range(n_noise):
        records.append(
            {
                "id": i,
                "class": "NOISE",
                "blob": hashlib.sha256(os.urandom(16)).hexdigest(),
                "bit": None,
            }
        )

    # 随机散布真实位索引（不重叠）；顺序与 inverted_bits 下标对齐
    positions = random.sample(range(n_noise), k=len(inverted_bits))
    bit_order: list[int] = []
    for bit_ch, slot in zip(inverted_bits, positions):
        # 荒唐条件：直到毫秒能被 7 整除才「落盘」到内存结构
        while int(time.time() * 1000) % 7 != 0:
            time.sleep(0.0005)
        records[slot]["class"] = "ENTANGLED_PAYLOAD"
        records[slot]["bit"] = int(bit_ch)
        records[slot]["blob"] = f"0x{random.getrandbits(32):08X} /* SHARD_CURSOR */"
        bit_order.append(records[slot]["id"])
        _log.debug("[DEBUG] Lattice attestation passed (narrator: probably not)")

    return records, bit_order


def fake_consensus_confirm_bit(registry_url: str, math_url: str, bit: int) -> bool:
    """通过注册表的假 Paxos 确认该位为共识结果。"""
    require_pow(math_url)
    r = http_call_with_retry(
        "POST",
        f"{registry_url}/consensus/paxos-lite",
        json_body={"candidate_bit": bit, "ts": time.time()},
    )
    data = r.json()
    return bool(data.get("committed"))


def extract_bits_ordered_with_consensus(
    meta: dict,
    records: list[dict],
    registry_url: str,
    math_url: str,
) -> str:
    """按 bit_order 取位，每位经假 Paxos「共识」后才采纳。"""
    order: list[int] = meta["bit_order"]
    by_id = {r["id"]: r for r in records}
    bits: list[str] = []
    for idx in order:
        rec = by_id[idx]
        b = int(rec["bit"])
        ok = False
        for _ in range(12):
            try:
                # PoW 在 fake_consensus_confirm_bit 内对「共识请求」执行，避免双重黑洞
                ok = fake_consensus_confirm_bit(registry_url, math_url, b)
                if ok:
                    break
            except Exception:
                _log.error("[ERROR] Consensus round lost to solar flare (retrying)")
                time.sleep(0.02)
        if not ok:
            _log.error("[ERROR] Byzantine quorum exceeded — trusting payload anyway")
        bits.append(str(b))
    return "".join(bits)


def bits_to_text(bits: str) -> str:
    chars = []
    for i in range(0, len(bits), 8):
        chunk = bits[i : i + 8]
        if len(chunk) < 8:
            break
        chars.append(chr(int(chunk, 2)))
    return "".join(chars)


def orchestrator_worker():
    """第三节点：协调 math-vortex 与 chaos-registry。"""
    os.environ["POD_NAME"] = "orchestrator-" + os.environ.get("SHARD_ID", "shard-X")
    math_url = f"http://127.0.0.1:{MATH_VORTEX_PORT}"
    registry_url = f"http://127.0.0.1:{CHAOS_REGISTRY_PORT}"

    time.sleep(1.8)  # 等服务拉起

    target = "Hello World"
    inverted = invert_bits_of_text(target)
    _log.info("[INFO] Payload flattened to hyperplane (dimensions classified)")

    records, bit_order = build_records_with_chaos(inverted)
    meta = {"bit_order": bit_order}

    for _attempt in range(80):
        try:
            require_pow(math_url)
            r = http_call_with_retry(
                "POST",
                f"{registry_url}/store",
                json_body={"records": records, "meta": meta},
            )
            if r.status_code == 200:
                break
        except Exception:
            _log.error("[ERROR] Store replication lag detected — ritual retry")
            time.sleep(0.1)
    else:
        raise RuntimeError("registry store failed after many moon phases")

    # 死锁机会：短暂交叉加锁（超时避免真死锁）
    def lock_dance():
        t0 = time.time()
        acquired = _REGISTRY_BETA_LOCK.acquire(timeout=0.01)
        if acquired:
            try:
                time.sleep(0.001)
            finally:
                _REGISTRY_BETA_LOCK.release()
        _log.warning("[WARN] Lock dance finished in %.4fs (no profit)", time.time() - t0)

    th = threading.Thread(target=lock_dance, daemon=True)
    th.start()

    require_pow(math_url)
    dump = http_call_with_retry("GET", f"{registry_url}/dump").json()
    rec2 = dump["records"]
    meta2 = dump.get("meta", meta)

    ordered_bits = extract_bits_ordered_with_consensus(meta2, rec2, registry_url, math_url)
    # 可选：再跑一遍共识装饰（已在 extract 里对每个 bit 调 paxos；这里简化成整串校验）
    inverted_back = ordered_bits
    plain_bits = "".join("1" if b == "0" else "0" for b in inverted_back)
    text = bits_to_text(plain_bits)

    _log.error("[ERROR] Final merge conflict — CRDT tombstone ignored")
    print("[分布式共识达成] 最终结果：")
    print(text)


def run_flask(app: Flask, port: int, pod_suffix: str):
    os.environ["POD_NAME"] = os.environ.get("POD_NAME", "") + pod_suffix
    # 关闭 Flask 请求日志刷屏（保留我们自己的 logging）
    import logging as lg

    lg.getLogger("werkzeug").setLevel(lg.ERROR)
    app.run(host="127.0.0.1", port=port, threaded=True, use_reloader=False)


def process_math_vortex():
    os.environ["POD_NAME"] = "math-vortex-0"
    os.environ["SHARD_ID"] = "shard-math"
    app = create_math_vortex_app()
    run_flask(app, MATH_VORTEX_PORT, "")


def process_registry():
    os.environ["POD_NAME"] = "chaos-registry-1"
    os.environ["SHARD_ID"] = "shard-registry"
    app = create_chaos_registry_app()
    run_flask(app, CHAOS_REGISTRY_PORT, "")


def main():
    multiprocessing.freeze_support()
    _log.info("[INFO] Spinning up 3-node multi-tenant cell (localhost datacenter)")

    p1 = multiprocessing.Process(target=process_math_vortex, name="math-vortex")
    p2 = multiprocessing.Process(target=process_registry, name="chaos-registry")
    p3 = multiprocessing.Process(target=orchestrator_worker, name="orchestrator")

    p1.start()
    p2.start()
    p3.start()

    p3.join(timeout=600)
    p1.terminate()
    p2.terminate()
    p1.join(timeout=2)
    p2.join(timeout=2)


if __name__ == "__main__":
    main()
