"""
Demo Portfolio Bridge Endpoint
Temporary endpoint to serve portfolio data from report files
"""

from fastapi import APIRouter, HTTPException
import json
import csv
from pathlib import Path
from typing import Dict, Any, List

router = APIRouter()

@router.get("/demo/{portfolio_type}")
async def get_demo_portfolio(portfolio_type: str) -> Dict[str, Any]:
    """
    Get demo portfolio data from report files.
    Currently only supports 'high-net-worth' portfolio.
    
    Args:
        portfolio_type: Type of portfolio ('high-net-worth')
    
    Returns:
        Dictionary containing portfolio info, exposures, and positions
    """
    
    # For now, only support high-net-worth
    if portfolio_type != 'high-net-worth':
        raise HTTPException(
            status_code=404, 
            detail=f"Portfolio type '{portfolio_type}' not implemented. Only 'high-net-worth' is currently supported."
        )
    
    # Map portfolio type to folder name
    folder_map = {
        'high-net-worth': 'demo-high-net-worth-portfolio_2025-08-23'
    }
    
    folder_name = folder_map.get(portfolio_type)
    if not folder_name:
        raise HTTPException(status_code=404, detail="Portfolio type not found")
    
    # Construct path to reports folder
    # Go up from current file to reach backend/reports
    current_file = Path(__file__)
    backend_dir = current_file.parent.parent.parent.parent.parent  # Up to backend/
    reports_dir = backend_dir / "reports" / folder_name
    
    # Debug logging
    print(f"Looking for reports in: {reports_dir}")
    print(f"Directory exists: {reports_dir.exists()}")
    
    if not reports_dir.exists():
        raise HTTPException(
            status_code=500, 
            detail=f"Report directory not found: {reports_dir}"
        )
    
    # Read JSON file for exposures and portfolio info
    json_path = reports_dir / "portfolio_report.json"
    print(f"Looking for JSON at: {json_path}")
    print(f"JSON file exists: {json_path.exists()}")
    
    if not json_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"JSON report file not found: {json_path}"
        )
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse JSON file: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read JSON file: {str(e)}"
        )
    
    # Read CSV file for position details
    csv_path = reports_dir / "portfolio_report.csv"
    print(f"Looking for CSV at: {csv_path}")
    print(f"CSV file exists: {csv_path.exists()}")
    
    if not csv_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"CSV report file not found: {csv_path}"
        )
    
    positions = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            positions = list(reader)
            print(f"Successfully read {len(positions)} positions from CSV")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read CSV file: {str(e)}"
        )
    
    # Extract relevant data from JSON
    portfolio_info = json_data.get("portfolio_info", {})
    position_exposures = json_data.get("calculation_engines", {}).get("position_exposures", {}).get("data", {})
    portfolio_snapshot = json_data.get("calculation_engines", {}).get("portfolio_snapshot", {}).get("data", {})
    
    # Return structured response
    response = {
        "portfolio_type": portfolio_type,
        "portfolio_info": portfolio_info,
        "exposures": position_exposures,
        "snapshot": portfolio_snapshot,
        "positions": positions,
        "metadata": {
            "source": "report_files",
            "report_date": json_data.get("metadata", {}).get("report_date", ""),
            "position_count": len(positions)
        }
    }
    
    print(f"Returning response with {len(positions)} positions")
    return response