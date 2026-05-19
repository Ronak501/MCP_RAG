"""Example runners for surveillance system"""
from __future__ import annotations

import argparse
from api.surveillance_api import SurveillanceAPI

def basic_demo():
    print("Running basic demo - this will use local example sources")

def rag_demo():
    print("Running RAG-enhanced demo - requires AI keys and models")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["basic", "rag"], default="basic")
    args = parser.parse_args()

    if args.mode == "basic":
        basic_demo()
    else:
        rag_demo()


if __name__ == "__main__":
    main()
