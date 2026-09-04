// frontend/src/routes/AppRoutes.tsx
import { Navigate, Route, Routes } from "react-router-dom";

import { ForgotPasswordPage } from "../features/auth/ForgotPasswordPage";
import { LoginPage } from "../features/auth/LoginPage";
import { ResetPasswordPage } from "../features/auth/ResetPasswordPage";
import { HealthStatus } from "../features/health/HealthStatus";
import { JournalEntriesPage } from "../features/journalEntries/JournalEntriesPage";
import { OwnersPage } from "../features/owners/OwnersPage";
import { PropertiesPage } from "../features/properties/PropertiesPage";
import { TenantsPage } from "../features/tenants/TenantsPage";
import { UnitsPage } from "../features/units/UnitsPage";
import { UsersPage } from "../features/users/UsersPage";
import { MainLayout } from "../layouts/MainLayout";
import { AdminRoute } from "./AdminRoute";
import { ProtectedRoute } from "./ProtectedRoute";
import { ResolutionsPage } from "../features/resolutions/ResolutionsPage";
// frontend/src/routes/AppRoutes.tsx — Imports + Routes ergänzen
import { BudgetPlansPage } from "../features/budgetPlans/BudgetPlansPage";
import { SpecialAssessmentsPage } from "../features/specialAssessments/SpecialAssessmentsPage";
// frontend/src/routes/AppRoutes.tsx — Import + Route ergänzen
import { SettlementPeriodsPage } from "../features/settlementPeriods/SettlementPeriodsPage";
// frontend/src/routes/AppRoutes.tsx — Imports + Route ergänzen
import { BankAccountsPage } from "../features/bankAccounts/BankAccountsPage";
import { MeetingsPage } from "../features/meetings/MeetingsPage";
import { AllocationKeysPage } from "../features/allocationKeys/AllocationKeysPage";
// ...

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      <Route element={<MainLayout />}>
        <Route path="/" element={<ProtectedRoute><HealthStatus /></ProtectedRoute>} />
        <Route path="/properties" element={<ProtectedRoute><PropertiesPage /></ProtectedRoute>} />
        <Route path="/units" element={<ProtectedRoute><UnitsPage /></ProtectedRoute>} />
        <Route path="/owners" element={<ProtectedRoute><OwnersPage /></ProtectedRoute>} />
        <Route path="/tenants" element={<ProtectedRoute><TenantsPage /></ProtectedRoute>} />
        <Route path="/journal-entries" element={<ProtectedRoute><JournalEntriesPage /></ProtectedRoute>} />
        <Route path="/resolutions" element={<ProtectedRoute><ResolutionsPage /></ProtectedRoute>} />
        <Route path="/budget-plans" element={<ProtectedRoute><BudgetPlansPage /></ProtectedRoute>} />
        <Route path="/special-assessments" element={<ProtectedRoute><SpecialAssessmentsPage /></ProtectedRoute>} />
        <Route path="/settlement-periods" element={<ProtectedRoute><SettlementPeriodsPage /></ProtectedRoute>} />
        <Route path="/bank-accounts" element={<ProtectedRoute><BankAccountsPage /></ProtectedRoute>} />
        <Route path="/meetings" element={<ProtectedRoute><MeetingsPage /></ProtectedRoute>} />
        <Route path="/allocation-keys" element={<ProtectedRoute><AllocationKeysPage /></ProtectedRoute>} />
        <Route
          path="/users"
          element={
            <ProtectedRoute>
              <AdminRoute>
                <UsersPage />
              </AdminRoute>
            </ProtectedRoute>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}