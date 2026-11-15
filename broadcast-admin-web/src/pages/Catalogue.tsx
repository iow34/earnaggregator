import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";

interface Product {
  id: string; symbol: string; provider: string; apy: number;
  product_type: string; lock_period_days: number;
}

export const CataloguePage = () => {
  const [symbol, setSymbol] = useState("");
  const products = useQuery({
    queryKey: ["catalogue", symbol],
    queryFn: async () => {
      const { data } = await apiClient.get<{ data: Product[] }>("/v1/products", {
        params: { symbol: symbol || undefined },
      });
      return data.data;
    },
  });
  return <section className="page">
    <header><h1>Earn catalogue</h1><p>Compare annual yield and lock periods across exchanges.</p></header>
    <label>Asset <select value={symbol} onChange={event => setSymbol(event.target.value)}>
      <option value="">All assets</option>
      {["BTC", "ETH", "SOL", "USDC", "USDT"].map(asset => <option key={asset}>{asset}</option>)}
    </select></label>
    {products.isError && <p role="alert" className="error">Could not load products. Check the API connection.</p>}
    {products.isLoading ? <p>Loading catalogue…</p> : <div className="card"><table className="data-table">
      <thead><tr><th>Asset</th><th>Exchange</th><th>APY</th><th>Product</th><th>Lock period</th></tr></thead>
      <tbody>{products.data?.map(item => <tr key={item.id}><td>{item.symbol}</td><td>{item.provider}</td>
        <td>{item.apy.toFixed(2)}%</td><td>{item.product_type}</td><td>{item.lock_period_days ? `${item.lock_period_days} days` : "Flexible"}</td></tr>)}</tbody>
    </table></div>}
  </section>;
};
