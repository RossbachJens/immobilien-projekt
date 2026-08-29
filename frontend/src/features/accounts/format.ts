// frontend/src/features/accounts/format.ts
import type { Account } from "./api";

function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 1).trimEnd()}…`;
}

type AccountLabelInput = Pick<Account, "account_number" | "account_name">;

/** Voller Name – für title-Attribute (Tooltip) und Tabellen mit CSS-Ellipsis. */
export function accountLabel(account: AccountLabelInput): string {
  return `${account.account_number} – ${account.account_name}`;
}

/** Gekürzter Name – nur für <option>, da dort CSS-Ellipsis nicht greift. */
export function accountLabelShort(account: AccountLabelInput, maxNameLength = 45): string {
  return `${account.account_number} – ${truncate(account.account_name, maxNameLength)}`;
}