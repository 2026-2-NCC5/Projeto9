import asyncio
import time
import statistics
import json
import httpx
import subprocess

BASE_URL = "http://localhost:5173"

def get_docker_stats():
    """Captura uso real de CPU e Memória dos contêineres Docker via CLI."""
    try:
        out = subprocess.check_output(
            ["docker", "stats", "--no-stream", "--format", "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}"],
            text=True,
            timeout=10
        )
        lines = out.strip().split("\n")
        stats = {}
        for l in lines:
            if "|" in l:
                name, cpu, mem, mem_p = l.split("|")
                stats[name.strip()] = {
                    "cpu": cpu.strip(),
                    "mem_usage": mem.strip(),
                    "mem_perc": mem_p.strip()
                }
        return stats
    except Exception as e:
        return {"error": str(e)}

async def run_scenario(client, token, scenario_name, method, endpoint, payload=None, n_requests=30, concurrency=5):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if payload:
        headers["Content-Type"] = "application/json"

    semaphore = asyncio.Semaphore(concurrency)
    latencies = []
    status_codes = {}
    errors = 0

    async def single_request(req_id):
        nonlocal errors
        async with semaphore:
            start = time.perf_counter()
            try:
                if method == "GET":
                    resp = await client.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=30.0)
                else:
                    body = payload.copy() if payload else {}
                    if "question" in body:
                        body["conversation_id"] = f"load-test-{scenario_name}-{req_id}"
                    resp = await client.post(f"{BASE_URL}{endpoint}", json=body, headers=headers, timeout=30.0)

                latency_ms = (time.perf_counter() - start) * 1000
                latencies.append(latency_ms)
                status_codes[resp.status_code] = status_codes.get(resp.status_code, 0) + 1
                if resp.status_code >= 400:
                    errors += 1
            except Exception as ex:
                latency_ms = (time.perf_counter() - start) * 1000
                latencies.append(latency_ms)
                errors += 1
                err_key = f"EX_{type(ex).__name__}"
                status_codes[err_key] = status_codes.get(err_key, 0) + 1

    tasks = [single_request(i) for i in range(n_requests)]
    t_start = time.perf_counter()
    await asyncio.gather(*tasks)
    total_time_s = time.perf_counter() - t_start

    sorted_lat = sorted(latencies) if latencies else [0]
    p50 = statistics.median(sorted_lat) if sorted_lat else 0
    p95 = sorted_lat[int(len(sorted_lat) * 0.95)] if sorted_lat else 0
    p99 = sorted_lat[int(len(sorted_lat) * 0.99)] if sorted_lat else 0
    avg_lat = statistics.mean(sorted_lat) if sorted_lat else 0
    throughput = n_requests / total_time_s if total_time_s > 0 else 0

    return {
        "scenario": scenario_name,
        "endpoint": endpoint,
        "concurrency": concurrency,
        "total_requests": n_requests,
        "total_time_seconds": round(total_time_s, 3),
        "throughput_rps": round(throughput, 2),
        "avg_latency_ms": round(avg_lat, 2),
        "p50_latency_ms": round(p50, 2),
        "p95_latency_ms": round(p95, 2),
        "p99_latency_ms": round(p99, 2),
        "error_count": errors,
        "error_rate_perc": round((errors / n_requests) * 100, 2),
        "status_distribution": status_codes
    }

async def main():
    print("=== INICIANDO AUDITORIA DE CARGA E OBSERVABILIDADE ===")
    initial_stats = get_docker_stats()
    print("Métricas iniciais em repouso (Docker Stats):")
    print(json.dumps(initial_stats, indent=2))

    async with httpx.AsyncClient(limits=httpx.Limits(max_keepalive_connections=50, max_connections=100)) as client:
        # Obter token da estudante Ana
        login_resp = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "ana.silva@fecap.br", "password": "demo1234"},
            timeout=10.0
        )
        token = login_resp.json().get("access_token")
        assert token, "Falha ao obter token JWT de estudante!"
        print(f"Token obtido com sucesso. Iniciando bateria de testes...")

        # Bateria 1: Healthcheck (Liveness / Throughput básico Nginx -> FastAPI)
        print("\n--- Bateria 1: Healthcheck (C=5, N=50) ---")
        res_health = await run_scenario(client, None, "Healthcheck", "GET", "/health", n_requests=50, concurrency=5)
        print(f"Throughput: {res_health['throughput_rps']} req/s | Média: {res_health['avg_latency_ms']}ms | p95: {res_health['p95_latency_ms']}ms | Erros: {res_health['error_rate_perc']}%")

        # Bateria 2: Perfil do Estudante (Autenticado, consulta SQLite)
        print("\n--- Bateria 2: Perfil Acadêmico (C=5, N=40) ---")
        res_profile = await run_scenario(client, token, "Perfil Estudante", "GET", "/api/v1/student/profile", n_requests=40, concurrency=5)
        print(f"Throughput: {res_profile['throughput_rps']} req/s | Média: {res_profile['avg_latency_ms']}ms | p95: {res_profile['p95_latency_ms']}ms | Erros: {res_profile['error_rate_perc']}%")

        # Bateria 3: Boletos Pendentes (Módulo Financeiro, consulta e formatação)
        print("\n--- Bateria 3: Consulta Financeira de Boletos (C=5, N=30) ---")
        res_boletos = await run_scenario(client, token, "Boletos Pendentes", "GET", "/api/v1/boletos/pending", n_requests=30, concurrency=5)
        print(f"Throughput: {res_boletos['throughput_rps']} req/s | Média: {res_boletos['avg_latency_ms']}ms | p95: {res_boletos['p95_latency_ms']}ms | Erros: {res_boletos['error_rate_perc']}%")

        # Bateria 4: Consulta RAG Acadêmico (IA + Busca Vetorial ChromaDB + Embedding)
        print("\n--- Bateria 4: RAG Pipeline - Baixa Concorrência (C=2, N=10) ---")
        rag_payload = {"question": "Como solicitar meu histórico escolar oficial?"}
        res_rag_c2 = await run_scenario(client, token, "RAG Acadêmico (C=2)", "POST", "/api/v1/agent/query", payload=rag_payload, n_requests=10, concurrency=2)
        print(f"Throughput: {res_rag_c2['throughput_rps']} req/s | Média: {res_rag_c2['avg_latency_ms']}ms | p95: {res_rag_c2['p95_latency_ms']}ms | Erros: {res_rag_c2['error_rate_perc']}%")

        print("\n--- Bateria 5: RAG Pipeline - Concorrência Moderada (C=5, N=20) ---")
        res_rag_c5 = await run_scenario(client, token, "RAG Acadêmico (C=5)", "POST", "/api/v1/agent/query", payload=rag_payload, n_requests=20, concurrency=5)
        print(f"Throughput: {res_rag_c5['throughput_rps']} req/s | Média: {res_rag_c5['avg_latency_ms']}ms | p95: {res_rag_c5['p95_latency_ms']}ms | Erros: {res_rag_c5['error_rate_perc']}%")

        # Capturar métricas do Docker sob/após carga
        post_stats = get_docker_stats()
        print("\nMétricas de telemetria sob/após carga (Docker Stats):")
        print(json.dumps(post_stats, indent=2))

        # Obter métricas consolidadas do Dashboard Administrativo
        login_admin = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "admin@fecap.br", "password": "admin1234"},
            timeout=10.0
        )
        admin_token = login_admin.json().get("access_token")
        dash_resp = await client.get(
            f"{BASE_URL}/api/v1/dashboard/",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10.0
        )
        dash_metrics = dash_resp.json()

        full_report = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "telemetry_initial": initial_stats,
            "telemetry_after_load": post_stats,
            "scenarios": [
                res_health,
                res_profile,
                res_boletos,
                res_rag_c2,
                res_rag_c5
            ],
            "dashboard_metrics": dash_metrics
        }

        with open("load_test_results.json", "w", encoding="utf-8") as f:
            json.dump(full_report, f, indent=2, ensure_ascii=False)
        print("\n=== TESTES CONCLUÍDOS COM SUCESSO! Relatório salvo em load_test_results.json ===")

if __name__ == "__main__":
    asyncio.run(main())
