# Real-chain proof

The attribution pipeline is **real-chain-ready**: it consumes the standard
Etherscan `account/txlist` schema and runs traversal + signals + attribution on it
unchanged.

- `kraken_depositor_216b7523.json` — a **genuine** low-degree wallet
  (`0x216b75231dfec0a4716b602ab00669fa568ad09b`, 12 real txs) captured live from
  Blockscout's Etherscan-compatible API. It deposits ETH to **Kraken's** public hot
  wallet (tx `0x52f9341275b49db16a206875b0f5370c78c7b836c0bc604abeae4365764dd148`
  — verify on any explorer). Our unchanged pipeline attributes it to **Kraken
  (~0.76)** on this real data. Seeded automatically by `run.ps1`.
- `sample_etherscan_txlist.json` — an **illustrative** example of the Etherscan
  response *shape* (not verified real transactions), kept for schema reference.

## Capture a real low-degree wallet (offline replay)

Pick a low-degree address that deposits to a known exchange, snapshot it once with
an API key, commit the snapshot, and the demo replays it offline — **no live
hot-wallet traversal in the demo**:

```bash
# needs ETHERSCAN_API_KEY in the environment / .env
python -m app.ingest.chain_import --address 0xYOURADDR --save data/realchain/real_case.json
# later, offline:
python -m app.ingest.chain_import --file data/realchain/real_case.json
```

Then open that address in the UI, or call `/wallets/{addr}/attribution`.
