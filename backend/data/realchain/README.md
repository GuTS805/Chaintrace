# Real-chain proof

The attribution pipeline is **real-chain-ready**: it consumes the standard
Etherscan `account/txlist` schema and runs traversal + signals + attribution on it
unchanged.

- `sample_etherscan_txlist.json` — an **illustrative** example of the Etherscan
  response *shape* (not verified real transactions). It reaches Binance's real,
  publicly-labeled hot wallet so you can watch the same pipeline attribute
  imported data.

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
