#!/usr/bin/env python3
"""
Load testing script for the ServerlessOrch API
"""

import argparse
import json
import uuid
import time
import random
import concurrent.futures
import statistics
from typing import Dict, Any, List, Tuple
import requests


def generate_random_order() -> Dict[str, Any]:
    """
    Generate a random order for testing
    
    Returns:
        Random order data
    """
    # List of sample products
    products = [
        {"id": "product-1", "name": "T-Shirt", "price": 19.99},
        {"id": "product-2", "name": "Jeans", "price": 49.99},
        {"id": "product-3", "name": "Jacket", "price": 89.99},
        {"id": "product-4", "name": "Sneakers", "price": 79.99},
        {"id": "product-5", "name": "Hat", "price": 24.99},
    ]
    
    # Generate a random customer ID
    customer_id = f"cust-{uuid.uuid4().hex[:8]}"
    
    # Generate random customer name
    first_names = ["John", "Jane", "Robert", "Mary", "Michael", "Linda", "William", "Elizabeth"]
    last_names = ["Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson"]
    name = f"{random.choice(first_names)} {random.choice(last_names)}"
    
    # Generate random email
    email = f"{name.lower().replace(' ', '.')}@example.com"
    
    # Select random products
    num_items = random.randint(1, 3)
    selected_products = random.sample(products, num_items)
    
    # Create order items
    items = []
    for product in selected_products:
        quantity = random.randint(1, 3)
        items.append({
            "product_id": product["id"],
            "quantity": quantity,
            "unit_price": product["price"]
        })
    
    # Generate random address
    streets = ["Main St", "Oak Ave", "Maple Rd", "Washington Blvd", "Park Lane"]
    cities = ["Anytown", "Springfield", "Franklin", "Clinton", "Georgetown"]
    states = ["CA", "NY", "TX", "FL", "IL"]
    
    # Create the order
    order = {
        "customer": {
            "customer_id": customer_id,
            "email": email,
            "name": name
        },
        "items": items,
        "shipping_address": {
            "street": f"{random.randint(100, 999)} {random.choice(streets)}",
            "city": random.choice(cities),
            "state": random.choice(states),
            "postal_code": f"{random.randint(10000, 99999)}",
            "country": "US"
        },
        "payment": {
            "payment_method": random.choice(["credit_card", "paypal", "apple_pay"])
        }
    }
    
    return order


def create_order(api_url: str) -> Tuple[bool, float, Dict[str, Any]]:
    """
    Create an order via the API and measure response time
    
    Args:
        api_url: API Gateway URL
        
    Returns:
        Tuple of (success, response_time, response_data)
    """
    # Generate a random order
    order_data = generate_random_order()
    
    # Measure response time
    start_time = time.time()
    
    try:
        # Send POST request to create order
        response = requests.post(
            f"{api_url}/orders", 
            json=order_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        # Calculate response time
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Check if request was successful
        success = response.status_code == 201
        
        return success, response_time, response.json() if success else {"error": response.text}
    
    except Exception as e:
        # Calculate response time even for failures
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        return False, response_time, {"error": str(e)}


def get_order(api_url: str, order_id: str) -> Tuple[bool, float, Dict[str, Any]]:
    """
    Get an order via the API and measure response time
    
    Args:
        api_url: API Gateway URL
        order_id: ID of the order to retrieve
        
    Returns:
        Tuple of (success, response_time, response_data)
    """
    # Measure response time
    start_time = time.time()
    
    try:
        # Send GET request to retrieve order
        response = requests.get(
            f"{api_url}/orders/{order_id}",
            timeout=10
        )
        
        # Calculate response time
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Check if request was successful
        success = response.status_code == 200
        
        return success, response_time, response.json() if success else {"error": response.text}
    
    except Exception as e:
        # Calculate response time even for failures
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        return False, response_time, {"error": str(e)}


def run_load_test(api_url: str, num_requests: int, concurrency: int) -> Dict[str, Any]:
    """
    Run a load test against the API
    
    Args:
        api_url: API Gateway URL
        num_requests: Number of requests to make
        concurrency: Number of concurrent requests
        
    Returns:
        Test results
    """
    print(f"Running load test against {api_url}")
    print(f"Making {num_requests} requests with concurrency of {concurrency}")
    
    # Remove trailing slash from API URL if present
    api_url = api_url.rstrip("/")
    
    # Track successful and failed requests
    successes = 0
    failures = 0
    
    # Track response times
    create_response_times = []
    get_response_times = []
    
    # Track created order IDs
    order_ids = []
    
    # Use ThreadPoolExecutor for concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        # Submit create order tasks
        create_futures = [executor.submit(create_order, api_url) for _ in range(num_requests)]
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(create_futures):
            success, response_time, response_data = future.result()
            
            if success:
                successes += 1
                create_response_times.append(response_time)
                order_ids.append(response_data["order_id"])
            else:
                failures += 1
            
            # Print progress
            total_processed = successes + failures
            print(f"\rProcessed: {total_processed}/{num_requests} "
                 f"(Success: {successes}, Failed: {failures})", end="")
    
    print("\nCreation requests completed")
    
    # If we have created orders, test retrieving them
    if order_ids:
        print(f"Testing GET requests for {len(order_ids)} orders")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            # Submit get order tasks
            get_futures = [executor.submit(get_order, api_url, order_id) for order_id in order_ids]
            
            # Process results as they complete
            get_successes = 0
            get_failures = 0
            
            for future in concurrent.futures.as_completed(get_futures):
                success, response_time, _ = future.result()
                
                if success:
                    get_successes += 1
                    get_response_times.append(response_time)
                else:
                    get_failures += 1
                
                # Print progress
                total_processed = get_successes + get_failures
                print(f"\rGET Processed: {total_processed}/{len(order_ids)} "
                     f"(Success: {get_successes}, Failed: {get_failures})", end="")
        
        print("\nGET requests completed")
    
    # Calculate statistics
    results = {
        "total_requests": num_requests,
        "successful_creates": successes,
        "failed_creates": failures,
        "create_success_rate": (successes / num_requests) * 100 if num_requests > 0 else 0
    }
    
    if create_response_times:
        results.update({
            "create_response_time": {
                "min": min(create_response_times),
                "max": max(create_response_times),
                "avg": statistics.mean(create_response_times),
                "median": statistics.median(create_response_times),
                "p95": statistics.quantiles(create_response_times, n=20)[18] if len(create_response_times) > 20 else max(create_response_times),
                "p99": statistics.quantiles(create_response_times, n=100)[98] if len(create_response_times) > 100 else max(create_response_times)
            }
        })
    
    if get_response_times:
        results.update({
            "get_requests": len(order_ids),
            "successful_gets": get_successes,
            "failed_gets": get_failures,
            "get_success_rate": (get_successes / len(order_ids)) * 100 if order_ids else 0,
            "get_response_time": {
                "min": min(get_response_times),
                "max": max(get_response_times),
                "avg": statistics.mean(get_response_times),
                "median": statistics.median(get_response_times),
                "p95": statistics.quantiles(get_response_times, n=20)[18] if len(get_response_times) > 20 else max(get_response_times),
                "p99": statistics.quantiles(get_response_times, n=100)[98] if len(get_response_times) > 100 else max(get_response_times)
            }
        })
    
    return results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Load test the ServerlessOrch API")
    parser.add_argument("--api-url", required=True, help="API Gateway URL")
    parser.add_argument("--requests", type=int, default=100, help="Number of requests to make")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent requests")
    parser.add_argument("--output", help="Output file for results (JSON)")
    args = parser.parse_args()
    
    # Run the load test
    results = run_load_test(args.api_url, args.requests, args.concurrency)
    
    # Print results
    print("\n====== LOAD TEST RESULTS ======")
    print(f"Total Requests: {results['total_requests']}")
    print(f"Success Rate (Create): {results['create_success_rate']:.2f}%")
    
    if "create_response_time" in results:
        rt = results["create_response_time"]
        print("\nCREATE Response Times (ms):")
        print(f"  Min: {rt['min']:.2f}")
        print(f"  Max: {rt['max']:.2f}")
        print(f"  Avg: {rt['avg']:.2f}")
        print(f"  Median: {rt['median']:.2f}")
        print(f"  p95: {rt['p95']:.2f}")
        print(f"  p99: {rt['p99']:.2f}")
    
    if "get_response_time" in results:
        print(f"\nSuccess Rate (GET): {results['get_success_rate']:.2f}%")
        rt = results["get_response_time"]
        print("\nGET Response Times (ms):")
        print(f"  Min: {rt['min']:.2f}")
        print(f"  Max: {rt['max']:.2f}")
        print(f"  Avg: {rt['avg']:.2f}")
        print(f"  Median: {rt['median']:.2f}")
        print(f"  p95: {rt['p95']:.2f}")
        print(f"  p99: {rt['p99']:.2f}")
    
    # Save results to file if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()