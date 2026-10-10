/** Shared data shapes used on both the server and the client. */

export interface Transaction {
  id: number;
  /** ISO date: YYYY-MM-DD */
  date: string;
  description: string;
  /** Negative = expense, positive = income. */
  amount: number;
  account: string;
  currency: string;
  category: string;
  subcategory: string;
  notes: string;
}

/** A transaction row ready for insertion (no id yet, carries the dedup hash). */
export interface NewTransaction {
  date: string;
  description: string;
  amount: number;
  account: string;
  currency: string;
  category: string;
  subcategory: string;
  notes: string;
  hash: string;
}

export interface RuleRow {
  id: number;
  pattern: string;
  category: string;
  subcategory: string;
}

/** Most recent known running balance for one account, as stored on import. */
export interface AccountBalance {
  account: string;
  currency: string;
  balance: number;
  /** ISO date of the statement row the balance came from. */
  as_of: string;
}

/** Logical CSV field -> CSV column name (null = not present, use defaults). */
export interface ColumnMapping {
  date: string;
  description: string;
  amount: string;
  account: string | null;
  currency: string | null;
  balance: string | null;
}

export interface ImportOptions {
  defaultAccount: string;
  defaultCurrency: string;
  decimalComma: boolean;
  dayfirst: boolean;
  applyRules: boolean;
  deduceIncome: boolean;
}
