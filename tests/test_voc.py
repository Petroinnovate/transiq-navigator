"""Tests for transiq.voc."""
import pytest
from transiq.voc import capture_voc, ctq_tree, qfd_matrix, kano_classify


class TestCaptureVOC:
    def test_basic(self):
        voices = [
            {"need": "Less downtime", "source": "survey",
             "category": "reliability", "priority": 5},
            {"need": "Faster response", "source": "interview",
             "category": "speed", "priority": 3},
        ]
        result = capture_voc(voices)
        assert len(result["needs"]) == 2
        assert "reliability" in result["by_category"]
        assert result["total_needs"] == 2


class TestCTQTree:
    def test_basic(self):
        drivers = [
            {
                "driver": "Low failure rate",
                "ctqs": [
                    {"characteristic": "MTBF", "specification": ">1000 hrs", "unit": "hours"},
                    {"characteristic": "MTTR", "specification": "<4 hrs", "unit": "hours"},
                ],
            }
        ]
        result = ctq_tree("Reliable equipment", drivers)
        assert result["customer_need"] == "Reliable equipment"
        assert result["total_ctqs"] == 2


class TestQFDMatrix:
    def test_basic(self):
        customer_reqs = [
            {"requirement": "Durability", "importance": 5},
            {"requirement": "Speed", "importance": 3},
        ]
        tech_reqs = ["Material strength", "Motor power"]
        relationships = [
            [9, 1],  # Durability vs [Material, Motor]
            [1, 9],  # Speed vs [Material, Motor]
        ]
        result = qfd_matrix(customer_reqs, tech_reqs, relationships)
        assert len(result["absolute_importance"]) == 2
        # Material strength: 9*5 + 1*3 = 48
        # Motor power: 1*5 + 9*3 = 32
        assert result["absolute_importance"][0] > result["absolute_importance"][1]


class TestKanoClassify:
    def test_basic(self):
        features = [
            {"feature": "Safety shutoff", "functional": "expect", "dysfunctional": "dislike"},
            {"feature": "Color options", "functional": "like", "dysfunctional": "neutral"},
        ]
        result = kano_classify(features)
        assert "features" in result
        assert len(result["features"]) == 2
        # Each should have a classification
        for item in result["features"]:
            assert "classification" in item
