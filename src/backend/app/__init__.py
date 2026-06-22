"""KineTwin backend (FastAPI). Stateless analysis service.

Exposes the movement-metrics pipeline over HTTP so the React frontend can drop
two task videos (or pre-tracked landmark arrays) and get the Speed / Accuracy /
Quality report plus the Learned Non-Use verdict.
"""
