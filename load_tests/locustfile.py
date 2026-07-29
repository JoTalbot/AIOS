from locust import HttpUser, between, task


class AIOSUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def health_check(self):
        self.client.get("/health")

    @task(2)
    def list_platforms(self):
        self.client.get("/api/v1/platforms")

    @task(1)
    def get_features(self):
        self.client.get("/api/v1/features")

    @task(1)
    def graphql_query(self):
        query = '{"query": "{ templates { id name } }"}'
        self.client.post("/graphql", data=query, headers={"Content-Type": "application/json"})


class WebhookUser(HttpUser):
    wait_time = between(0.5, 1.5)

    @task
    def send_webhook(self):
        payload = {
            "entry": [
                {
                    "messaging": [
                        {
                            "sender": {"id": "test_user"},
                            "message": {"mid": "msg_123", "text": "Test message"},
                            "timestamp": 1234567890,
                        }
                    ]
                }
            ]
        }
        self.client.post("/webhooks/instagram", json=payload)
