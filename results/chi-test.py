import numpy as np
from scipy.stats import chi2_contingency

# Observed data
observed_counts = [1, 1, 1, 4, 3, 3, 3]  # 7 nodes are considered here. Change number by number of times each node is selected as a proposer

# Calculate the expected counts assuming equal probabilities for each selector
total_proposers = sum(observed_counts)
expected_counts = [total_proposers / 7] * 7

# Create a contingency table
observed = np.array([observed_counts])
expected = np.array([expected_counts])

# Perform the Chi-Squared test
chi2, p, _, _ = chi2_contingency(observed)

# Define the significance level (alpha)
alpha = 0.05

# Print the results
print("Chi-Squared Statistic:", chi2)
print("P-value:", p)

# Compare the p-value to the significance level
if p < alpha:
    print("Reject the null hypothesis: There is a significant difference in the selection of proposers.")
else:
    print("Fail to reject the null hypothesis: The selection of proposers appears to be random.")
