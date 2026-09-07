import numpy as np

from app.services.symptom_rag_service import _l2_normalize


def test_l2_normalize_returns_unit_vectors():
    arr = np.asarray([[3.0, 4.0], [0.0, 2.0]], dtype=np.float32)
    out = _l2_normalize(arr)
    norms = np.linalg.norm(out, axis=1)
    assert np.allclose(norms, np.asarray([1.0, 1.0]), atol=1e-6)
