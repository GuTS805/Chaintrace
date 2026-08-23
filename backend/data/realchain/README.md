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
- `binance_depositor_5b271663.json` — a second **genuine** low-degree wallet
  (`0x5b271663569cc0df548a81e2b56689be6999081c`, 4 real txs) that forwards ETH to
  **Binance's** public hot wallet (tx
  `0x1c8df3644db3e26e79bcff17ef4b1d8c111ae7d7e00000381b790aec350ccfc4`). The
  pipeline attributes it to **Binance (~0.76)**. An independent second-VASP proof.
- `sample_etherscan_txlist.json` — an **illustrative** example of the Etherscan
  response *shape* (not verified real transactions), kept for schema reference.
- `tron_kraken_depositor_TVYuaXdh.json` — a **genuine** low-degree Tron wallet
  (`TVYuaXdhEHBvmk8284pSdtyRZwxE5oZ9yQ`, 16 real USDT-TRC20 transfers) captured
  live from TronGrid's keyless API. It deposits USDT to **Kraken's** public Tron
  hot wallet (`TG2CMGxnTPgQ6V58kiKd7wbyN8ewtAmY76`, tx
  `6cc36b1392a879a3fd94f592dc45636184d1c460f6f62dfdcb8ffff4cf28fba0` — verify on
  any Tron explorer). The unchanged pipeline attributes it to **Kraken** on this
  real data — proof the multi-chain path works end to end, not just the EVM one.

## Capture a real low-degree wallet (offline replay)

Pick a low-degree address that deposits to a known exchange, snapshot it once with
an API key, commit the snapshot, and the demo replays it offline — **no live
hot-wallet traversal in the demo**:

```bash
# needs ETHERSCAN_API_KEY in the environment / .env
python -m app.ingest.chain_import --address 0xYOURADDR --save data/realchain/real_case.json
# later, offline:
python -m app.ingest.chain_import --file data/realchain/real_case.json --chain ethereum
```

Tron is keyless — no API key needed:

```bash
python -m app.ingest.chain_import --address TYOURADDR --save data/realchain/real_tron_case.json
# chain is auto-detected from the address shape (T... = tron); --file still
# needs --chain tron explicitly, since a saved JSON has no address to sniff.
python -m app.ingest.chain_import --file data/realchain/real_tron_case.json --chain tron
```

Then open that address in the UI, or call `/wallets/{addr}/attribution`.
