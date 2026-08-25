import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { apiClient } from "../api/client";
import { useAuth } from "../context/AuthContext";

interface HealthResponse {
  status: string;
}

function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const { data } = await apiClient.get<HealthResponse>("/health");
      return data;
    },
  });
}

export default function DashboardPage() {
  const { data, isLoading, isError } = useHealth();
  const { user, logout } = useAuth();

  return (
    <main style={{ fontFamily: "sans-serif", padding: "2rem" }}>
      <h1>Immobilien- &amp; WEG-Verwaltung</h1>
      <p>
        Backend-Status:{" "}
        {isLoading && "wird geprüft…"}
        {isError && "nicht erreichbar"}
        {data && `${data.status}`}
      </p>
      <p>Angemeldet als {user?.email}</p>
      <nav style={{ margin: "1rem 0" }}>
        <Link to="/properties">Liegenschaften</Link>
      </nav>
      <button onClick={() => logout()}>Abmelden</button>
    </main>
  );
}
