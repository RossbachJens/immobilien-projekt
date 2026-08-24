import { useQuery } from "@tanstack/react-query";

import { apiClient } from "./api/client";

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

export default function App() {
  const { data, isLoading, isError } = useHealth();

  return (
    <main style={{ fontFamily: "sans-serif", padding: "2rem" }}>
      <h1>Immobilien- &amp; WEG-Verwaltung</h1>
      <p>
        Backend-Status:{" "}
        {isLoading && "wird geprüft…"}
        {isError && "nicht erreichbar"}
        {data && `${data.status}`}
      </p>
    </main>
  );
}
