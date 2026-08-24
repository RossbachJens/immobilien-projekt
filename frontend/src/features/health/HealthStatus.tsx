import { Card } from "../../components/Card";
import { useHealth } from "./useHealth";

export function HealthStatus() {
  const { data, isLoading, isError } = useHealth();

  return (
    <Card>
      <h1>Backend-Status</h1>
      <p>
        {isLoading && "wird geprüft…"}
        {isError && "nicht erreichbar"}
        {data && data.status}
      </p>
    </Card>
  );
}
