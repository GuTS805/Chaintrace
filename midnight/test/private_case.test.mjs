// Copyright 2026 Chaintrace contributors. Licensed under Apache-2.0.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import * as RT from '@midnight-ntwrk/compact-runtime';
import { Contract, ledger } from '../managed/private_case/contract/index.js';

const coin = '0'.repeat(64);
const address = RT.sampleContractAddress();
const owner = new Uint8Array(32).fill(7);
const intruder = new Uint8Array(32).fill(8);
const commitment = new Uint8Array(32).fill(9);

function makeContract(secret) {
  return new Contract({ owner_secret: ({ privateState }) => [privateState, privateState.secret] });
}

test('owner can attest a digest; another private witness cannot', () => {
  const privateState = { secret: owner };
  const contract = makeContract(owner);
  const initial = contract.initialState(
    RT.createConstructorContext(privateState, coin),
    owner,
  );
  const context = RT.createCircuitContext(
    address, coin, initial.currentContractState, privateState,
  );
  const result = contract.impureCircuits.attest(context, commitment);
  const publicState = ledger(result.context.currentQueryContext.state);
  assert.deepEqual(publicState.case_commitment, commitment);
  assert.equal(publicState.revision, 1n);

  const wrongState = { secret: intruder };
  const wrongContext = RT.createCircuitContext(
    address, coin, result.context.currentQueryContext.state, wrongState,
  );
  assert.throws(
    () => contract.impureCircuits.attest(wrongContext, new Uint8Array(32).fill(3)),
    /Unauthorized attestation/,
  );
});
