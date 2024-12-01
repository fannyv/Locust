from locust import HttpUser, task, between, events
from prometheus_client import start_http_server, Summary, Counter, Gauge

# Définir les métriques Prometheus
MEDIAN_RESPONSE_TIME = Gauge('locust_stats_median_response_time', 'Median response time', ['path'])
AVG_RESPONSE_TIME = Gauge('locust_stats_avg_response_time', 'Average response time', ['path'])
NUM_REQUESTS = Counter('locust_stats_num_requests', 'Number of requests', ['path'])
NUM_FAILURES = Counter('locust_stats_num_failures', 'Number of failures', ['path'])
AVG_CONTENT_LENGTH = Gauge('locust_stats_avg_content_length', 'Average content length', ['path'])
USER_COUNT = Gauge('locust_user_count', 'Number of users')
FAIL_RATIO = Gauge('locust_fail_ratio', 'Failure ratio')
SLAVE_COUNT = Gauge('locust_slave_count', 'Number of slaves')
CURRENT_RPS = Gauge('locust_stats_current_rps', 'Current requests per second', ['path'])
CURRENT_FAIL_PER_SEC = Gauge('locust_stats_current_fail_per_sec', 'Current failures per second', ['path'])

# Démarrer un serveur Prometheus pour exposer les métriques
@events.init.add_listener
def start_metrics_server(environment, **kwargs):
    """
    Démarre le serveur Prometheus pour exposer les métriques sur le port 9100.
    """
    print("Démarrage du serveur Prometheus sur le port 9100...")
    start_http_server(9100)

# Suivi des requêtes pour mettre à jour les métriques
@events.request.add_listener
def track_requests(request_type, name, response_time, response_length, exception, **kwargs):
    """
    Met à jour les métriques pour chaque requête traitée par Locust.
    """
    path = name if name else "Aggregated"  # Utilise le chemin ou "Aggregated" par défaut

    # Temps de réponse
    AVG_RESPONSE_TIME.labels(path=path).set(response_time)  # Temps moyen de réponse
    MEDIAN_RESPONSE_TIME.labels(path=path).set(response_time)  # Médiane approximée avec le temps actuel

    # Longueur moyenne du contenu
    if response_length > 0:
        AVG_CONTENT_LENGTH.labels(path=path).set(response_length)

    # Requêtes et échecs
    NUM_REQUESTS.labels(path=path).inc()  # Incrémenter le nombre de requêtes
    if exception:
        NUM_FAILURES.labels(path=path).inc()  # Incrémenter le nombre d'échecs
        CURRENT_FAIL_PER_SEC.labels(path=path).set(1)  # Une erreur détectée
    else:
        CURRENT_FAIL_PER_SEC.labels(path=path).set(0)

# Suivi des utilisateurs et des RPS
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """
    Initialise les métriques lorsque le test commence.
    """
    USER_COUNT.set(environment.runner.user_count)  # Nombre d'utilisateurs actifs
    CURRENT_RPS.labels(path="Aggregated").set(0)  # Initialiser les RPS à 0
    FAIL_RATIO.set(0)  # Initialiser le ratio d'échec
    SLAVE_COUNT.set(0)  # Initialiser les slaves (utile pour le mode distribué)

@events.spawning_complete.add_listener
def on_spawning_complete(user_count, **kwargs):
    """
    Met à jour la métrique locust_user_count une fois que tous les utilisateurs sont générés.
    """
    USER_COUNT.set(user_count)

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    Réinitialise les métriques lorsque le test s'arrête.
    """
    USER_COUNT.set(0)  # Réinitialiser le nombre d'utilisateurs
    CURRENT_RPS.labels(path="Aggregated").set(0)  # Réinitialiser les RPS
    FAIL_RATIO.set(0)  # Réinitialiser le ratio d'échec
    SLAVE_COUNT.set(0)  # Réinitialiser le nombre de slaves

# Classe d'utilisateur simulé
class JSONPlaceholderUser(HttpUser):
    """
    Classe représentant un utilisateur simulé effectuant des requêtes vers l'API JSONPlaceholder.
    """
    wait_time = between(1, 3)  # Temps d'attente aléatoire entre les tâches (1 à 3 secondes)

    @task(3)
    def get_posts(self):
        """
        Effectue une requête GET vers l'endpoint /posts.
        """
        response = self.client.get("/posts")
        if response.status_code == 200:
            CURRENT_RPS.labels(path="/posts").inc()  # Mise à jour des RPS

    @task(2)
    def get_comments(self):
        """
        Effectue une requête GET vers l'endpoint /comments.
        """
        response = self.client.get("/comments")
        if response.status_code == 200:
            CURRENT_RPS.labels(path="/comments").inc()

    @task(1)
    def get_users(self):
        """
        Effectue une requête GET vers l'endpoint /users.
        """
        response = self.client.get("/users")
        if response.status_code == 200:
            CURRENT_RPS.labels(path="/users").inc()
