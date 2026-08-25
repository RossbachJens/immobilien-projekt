import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

import type { CurrentUser, LoginPayload } from "../api/auth";
import { fetchCurrentUser, login as loginRequest, logout as logoutRequest } from "../api/auth";

interface AuthContextValue {
  user: CurrentUser | null;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Prueft beim App-Start, ob noch ein gueltiges Cookie vorliegt.
    fetchCurrentUser()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setIsLoading(false));
  }, []);

  async function login(payload: LoginPayload) {
    const loggedInUser = await loginRequest(payload);
    setUser(loggedInUser);
  }

  async function logout() {
    await logoutRequest();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth muss innerhalb von <AuthProvider> verwendet werden");
  }
  return context;
}
