import Link from "next/link";
import { WalletSearch } from "@/components/WalletSearch";
import { Panel } from "@/components/ui";
import { DEMO_WALLETS, shortAddr } from "@/lib/format";

export default function Home() {
  return (
    <div className="mx-auto max-w-3xl space-y-6 pt-6">
      <div>
        <h1 className="text-lg font-semibold">Wallet attribution</h1>
        <p className="mt-1 text-sm text-muted">
          Enter a wallet address to attribute it to a likely VASP with a
          calibrated confidence score and a traceable evidence chain.
        </p>
      </div>

      <WalletSearch />

      <Panel title="Demo wallets (offline seeded)">
        <ul className="divide-y divide-border">
          {DEMO_WALLETS.map((w) => (
            <li key={w.address}>
              <Link
                href={`/wallets/${w.address}`}
                className="flex items-center gap-3 py-2.5 hover:bg-panel2"
              >
                <span className="w-44 font-semibold text-accent">{w.label}</span>
                <span className="text-muted">{shortAddr(w.address)}</span>
                <span className="ml-auto text-xs text-muted">{w.note}</span>
              </Link>
            </li>
          ))}
        </ul>
      </Panel>

      <p className="text-xs text-muted">
        Run <code className="text-text">make seed-demo</code> and start the API
        first. Manage investigations under{" "}
        <Link href="/cases" className="text-accent hover:underline">
          cases
        </Link>
        .
      </p>
    </div>
  );
}
