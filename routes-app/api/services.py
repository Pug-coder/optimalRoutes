"""
Service provider for API routes.
This file initializes service instances to be used across API routes.
"""
from services.route_optimizer import RouteOptimizer
from services.genetic_optimizer import GeneticOptimizer

# Create singleton instances of services
route_optimizer = RouteOptimizer()
genetic_optimizer = GeneticOptimizer(
    population_size=100,
    max_generations=100,
    mutation_rate=0.1,
    crossover_rate=0.8,
    elitism_rate=0.1,
    timeout_seconds=30
)

# Export services to be used in routes
__all__ = ["route_optimizer", "genetic_optimizer"] 