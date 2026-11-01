export const DCF_BASE = {
  revenues: [1200000000, 2500000000, 4200000000, 5800000000, 7000000000],
  costs: [750000000, 1400000000, 2150000000, 2850000000, 3400000000],
  capex: [350000000, 150000000, 100000000, 100000000, 100000000],
  workingCapital: [50000000, 75000000, 90000000, 80000000, 60000000],
  taxRate: 0.22,
};

export interface DcfRow {
  year: number;
  fcf: number;
  pv: number;
}

export function computeDcf(discountRate: number, attribution: number, revenueFactor: number) {
  const rows: DcfRow[] = [];
  let npv = 0;
  for (let t = 0; t < DCF_BASE.revenues.length; t++) {
    const ebit = DCF_BASE.revenues[t] * revenueFactor - DCF_BASE.costs[t];
    const nopat = ebit >= 0 ? ebit * (1 - DCF_BASE.taxRate) : ebit;
    const fcf = (nopat - DCF_BASE.capex[t] - DCF_BASE.workingCapital[t]) * attribution;
    const pv = fcf / Math.pow(1 + discountRate, t + 1);
    npv += pv;
    rows.push({ year: t + 1, fcf, pv });
  }
  return { npv, rows };
}

export function formatRupiah(value: number): string {
  const rounded = Math.round(value);
  const sign = rounded < 0 ? "-" : "";
  return `${sign}Rp ${Math.abs(rounded).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".")}`;
}

export function formatMillions(value: number): string {
  return `${(value / 1e6).toLocaleString("id-ID", { maximumFractionDigits: 0 })} jt`;
}
