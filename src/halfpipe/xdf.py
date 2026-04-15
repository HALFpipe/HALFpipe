import numpy as np
import scipy.signal
import scipy.stats
from numba import guvectorize, objmode
from numpy import typing as npt


@guvectorize(
    ["void(float64[:], float64[:])"],
    "(n)->(n)",
    nopython=True,
)
def calculate_autocorrelation(time_series: npt.NDArray[np.float64], autocorrelations: npt.NDArray[np.float64]) -> None:
    with objmode(autocovariance="float64[:]"):
        autocovariance = scipy.signal.correlate(time_series, time_series, mode="full", method="fft")
    n = np.sum(np.square(time_series))

    start = time_series.size - 1
    end = start + time_series.size

    autocorrelations[:] = autocovariance[start:end] / n


@guvectorize(
    ["void(float64[:], float64[:], int64[:], float64[:], float64[:], float64[:], float64[:])"],
    "(n),(n),(),(p),(p)->(),()",
    nopython=True,
)
def calculate_variance(
    time_series_a: npt.NDArray[np.float64],
    time_series_b: npt.NDArray[np.float64],
    breakpoints: npt.NDArray[np.int64],
    autocorrelations_a: npt.NDArray[np.float64],
    autocorrelations_b: npt.NDArray[np.float64],
    correlation: npt.NDArray[np.float64],
    variance: npt.NDArray[np.float64],
):
    correlation[0] = np.corrcoef(time_series_a, time_series_b)[0, 1]

    with objmode(positive_lag_crosscorrelation="float64[:]"):
        positive_lag_crosscorrelation = scipy.signal.correlate(time_series_a, time_series_b, mode="full", method="fft")
    with objmode(negative_lag_crosscorrelation="float64[:]"):
        negative_lag_crosscorrelation = scipy.signal.correlate(time_series_b, time_series_a, mode="full", method="fft")

    length = time_series_a.size
    start = length
    end = start + length - 2
    n = np.sqrt(np.square(time_series_a).sum() * np.square(time_series_b).sum())
    positive_lag_crosscorrelation = positive_lag_crosscorrelation[start:end] / n
    negative_lag_crosscorrelation = negative_lag_crosscorrelation[start:end] / n

    positive_lag_crosscorrelation[breakpoints[0] :] = 0.0
    negative_lag_crosscorrelation[breakpoints[0] :] = 0.0

    weights = np.arange(length - 2, 0, step=-1, dtype=np.float64)
    squared = np.dot(
        weights,
        np.square(autocorrelations_a)
        + np.square(autocorrelations_b)
        + np.square(positive_lag_crosscorrelation)
        + np.square(negative_lag_crosscorrelation),
    )
    product_sum = np.dot(
        weights,
        (autocorrelations_a + autocorrelations_b) * (positive_lag_crosscorrelation + negative_lag_crosscorrelation),
    )
    sum_product = np.dot(
        weights,
        autocorrelations_a * autocorrelations_b + positive_lag_crosscorrelation * negative_lag_crosscorrelation,
    )

    c = np.square(correlation[0])
    variance[0] = (
        (length - 1) * np.square(1.0 - c) + c * squared - 2.0 * correlation[0] * product_sum + 2.0 * sum_product
    ) / np.square(length)


def mask_autocorrelations(
    autocorrelations: npt.NDArray[np.float64],
) -> npt.NDArray[np.int64]:
    _, lag_count = autocorrelations.shape
    threshold = (np.sqrt(2.0) * 1.3859) / np.sqrt(lag_count)
    mask = np.abs(autocorrelations) < threshold
    breakpoints = np.argmax(mask, axis=1)
    indices = np.arange(lag_count)
    mask = indices >= breakpoints[:, np.newaxis]
    autocorrelations[mask] = 0.0
    return breakpoints


def xdf(
    time_series: npt.NDArray[np.float64],
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    count, length = time_series.shape
    time_series = scipy.stats.zscore(time_series, axis=1, ddof=1, nan_policy="omit")  # pyright: ignore[reportAssignmentType]
    (indices,) = np.nonzero(np.isfinite(time_series).all(axis=1))
    time_series = time_series[indices]

    autocorrelations = calculate_autocorrelation(time_series)[:, 1:-1]  # pyright: ignore[reportCallIssue]
    breakpoints = mask_autocorrelations(autocorrelations)

    effect = np.full((count, count), fill_value=np.nan)
    variance = np.full_like(effect, fill_value=np.nan)

    triangular_indices = np.vstack(np.tril_indices(indices.size, k=-1))
    count = max(1, triangular_indices.shape[1] // 100)
    for i, j in np.array_split(triangular_indices, count, axis=1):
        correlation_vector, variance_vector = calculate_variance(
            time_series[i],
            time_series[j],
            np.maximum(breakpoints[i], breakpoints[j]),
            autocorrelations[i],
            autocorrelations[j],
        )  # pyright: ignore[reportCallIssue]

        theoretical_minimum_variance = np.square(1.0 - np.square(correlation_vector)) / length
        variance_vector = np.maximum(variance_vector, theoretical_minimum_variance)

        effect[indices[i], indices[j]] = np.arctanh(correlation_vector)

        variance[indices[i], indices[j]] = variance_vector / np.square(1.0 - np.square(correlation_vector))

    return effect, variance
