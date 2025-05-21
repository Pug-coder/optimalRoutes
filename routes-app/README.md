## Optimization Algorithms

The application supports two optimization algorithms for route planning:

1. **OR-Tools Optimizer (Default)**: This uses Google's Operations Research tools, specifically the Vehicle Routing solution, to solve the Multi-Depot Vehicle Routing Problem (MDVRP).

2. **Genetic Algorithm Optimizer**: An alternative implementation that uses evolutionary computation principles to find good solutions. While potentially not as optimal as OR-Tools for some problems, it provides flexibility and customization options.

### Comparing the Optimizers

You can compare the performance and solution quality of both optimizers using the included test scripts:

- `test_standalone.py`: A standalone script that implements simplified versions of both algorithms for direct comparison without dependencies on the API structure.

- `test_genetic_vs_ortools.py`: A more comprehensive test that compares the full implementations as used in the API.

### API Endpoints for Optimization

- **OR-Tools optimization**: `POST /routes/optimize`
- **Genetic Algorithm optimization**: `POST /routes/optimize/genetic`

Both endpoints will return the optimized routes in the same format, making it easy to switch between algorithms or compare results.

### Customizing the Genetic Algorithm

The genetic algorithm can be customized by modifying the parameters in `api/services.py`:

```python
genetic_optimizer = GeneticOptimizer(
    population_size=100,  # Number of solutions in the population
    max_generations=100,  # Maximum iterations of the algorithm
    mutation_rate=0.1,    # Probability of mutating an individual (0-1)
    crossover_rate=0.8,   # Probability of crossing over two individuals (0-1)
    elitism_rate=0.1,     # Proportion of best individuals kept unchanged (0-1)
    timeout_seconds=30    # Maximum time to run in seconds
) 