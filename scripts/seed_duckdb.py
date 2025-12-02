"""
DuckDB Sample Data Generator
-----------------------------
Creates synthetic sales data for local development and testing.
Generates realistic sample data for dashboards without requiring SQL Server connection.

Tables created:
    - sales_mart.Sucursal (Branches/Locations)
    - sales_mart.Linea (Product categories)
    - sales_mart.Sub_Linea (Product subcategories)
    - sales_mart.Productos (Products)
    - sales_mart.Ventas (Sales transactions)

Author: Development Team
"""

import os
import random
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import pandas as pd


def create_sample_data():
    """
    Generate sample data for all tables in the sales_mart schema.

    Returns:
        Dictionary containing DataFrames for each table.
    """
    print(">> Generating sample data...")

    # =========================================================================
    # 1. Sucursal (Branches) - 10 locations
    # =========================================================================
    sucursales = pd.DataFrame({
        'id_sucursal': range(1, 11),
        'nombre': [
            'Centro CDMX',
            'Polanco',
            'Santa Fe',
            'Monterrey Centro',
            'Guadalajara Plaza',
            'Puebla Angelópolis',
            'Querétaro Centro',
            'Cancún Marina',
            'Tijuana Río',
            'Mérida Norte'
        ],
        'ciudad': [
            'Ciudad de México',
            'Ciudad de México',
            'Ciudad de México',
            'Monterrey',
            'Guadalajara',
            'Puebla',
            'Querétaro',
            'Cancún',
            'Tijuana',
            'Mérida'
        ],
        'estado': [
            'CDMX',
            'CDMX',
            'CDMX',
            'Nuevo León',
            'Jalisco',
            'Puebla',
            'Querétaro',
            'Quintana Roo',
            'Baja California',
            'Yucatán'
        ],
        'activo': [True] * 10
    })

    # =========================================================================
    # 2. Linea (Product Categories) - 5 main categories
    # =========================================================================
    lineas = pd.DataFrame({
        'id_linea': range(1, 6),
        'nombre': [
            'Electrónica',
            'Ropa y Accesorios',
            'Hogar y Decoración',
            'Deportes',
            'Alimentos y Bebidas'
        ],
        'descripcion': [
            'Dispositivos electrónicos y tecnología',
            'Prendas de vestir y accesorios de moda',
            'Artículos para el hogar y decoración',
            'Equipamiento deportivo y fitness',
            'Productos alimenticios y bebidas'
        ]
    })

    # =========================================================================
    # 3. Sub_Linea (Product Subcategories) - 15 subcategories
    # =========================================================================
    sub_lineas = pd.DataFrame({
        'id_sub_linea': range(1, 16),
        'id_linea': [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5],
        'nombre': [
            'Smartphones',
            'Laptops',
            'Accesorios Tech',
            'Ropa Hombre',
            'Ropa Mujer',
            'Calzado',
            'Muebles',
            'Decoración',
            'Iluminación',
            'Gimnasio',
            'Outdoor',
            'Natación',
            'Orgánicos',
            'Bebidas',
            'Snacks'
        ]
    })

    # =========================================================================
    # 4. Productos (Products) - 50 products
    # =========================================================================
    product_names = [
        # Electronics (15)
        'iPhone 15 Pro', 'Samsung Galaxy S24', 'Google Pixel 8',
        'MacBook Pro M3', 'Dell XPS 15', 'HP Spectre x360',
        'AirPods Pro', 'Sony WH-1000XM5', 'Anker PowerBank',
        'iPad Air', 'Samsung Tab S9', 'Kindle Paperwhite',
        'Apple Watch Series 9', 'Garmin Fenix 7', 'Fitbit Charge 6',
        # Clothing (10)
        'Camisa Formal', 'Jeans Premium', 'Vestido Casual',
        'Blusa Ejecutiva', 'Pantalón Chino', 'Falda Plisada',
        'Nike Air Max', 'Adidas Ultraboost', 'Converse Chuck Taylor', 'Vans Old Skool',
        # Home (10)
        'Sofá Modular', 'Mesa de Centro', 'Lámpara de Pie',
        'Cuadro Abstracto', 'Espejo Decorativo', 'Cojines Premium',
        'Escritorio Ejecutivo', 'Silla Ergonómica', 'Estantería Nordic', 'Alfombra Persa',
        # Sports (10)
        'Mancuernas Ajustables', 'Banda Elástica', 'Yoga Mat Premium',
        'Bicicleta Montaña', 'Patineta Eléctrica', 'Mochila Hiking',
        'Traje de Baño', 'Goggles Natación', 'Toalla Microfibra', 'Gorra Deportiva',
        # Food (5)
        'Quinoa Orgánica', 'Café Premium', 'Té Verde Matcha',
        'Proteína Whey', 'Barras Energéticas'
    ]

    productos = pd.DataFrame({
        'id_producto': range(1, 51),
        'nombre': product_names,
        'id_sub_linea': (
            [1]*3 + [2]*3 + [3]*9 +  # Electronics
            [4]*3 + [5]*3 + [6]*4 +  # Clothing
            [7]*4 + [8]*3 + [9]*3 +  # Home
            [10]*3 + [11]*3 + [12]*4 +  # Sports
            [13]*2 + [14]*1 + [15]*2  # Food
        ),
        'precio': [
            # Electronics
            25999, 22999, 18999, 45999, 32999, 28999,
            5499, 7999, 899, 15999, 12999, 3499,
            10999, 13999, 4999,
            # Clothing
            899, 1299, 799, 699, 999, 649,
            3499, 3299, 1899, 1799,
            # Home
            12999, 4999, 2499, 1899, 3499, 599,
            8999, 5999, 4499, 6999,
            # Sports
            2999, 399, 899, 15999, 8999, 2499,
            899, 599, 399, 299,
            # Food
            149, 399, 299, 899, 189
        ],
        'stock': [random.randint(10, 200) for _ in range(50)],
        'activo': [True] * 50
    })

    # =========================================================================
    # 5. Ventas (Sales) - 5000 transactions (last 12 months)
    # =========================================================================
    print(">> Generating 5000 sales transactions...")

    # Generate dates for last 12 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    sales_data = []
    for i in range(1, 5001):
        # Random date in the last year
        random_days = random.randint(0, 365)
        sale_date = start_date + timedelta(days=random_days)

        # Random product and quantity
        producto_id = random.randint(1, 50)
        cantidad = random.randint(1, 5)
        precio_unitario = productos[productos['id_producto'] == producto_id]['precio'].values[0]
        total = precio_unitario * cantidad

        # Random branch
        sucursal_id = random.randint(1, 10)

        sales_data.append({
            'id_venta': i,
            'id_producto': producto_id,
            'id_sucursal': sucursal_id,
            'fecha': sale_date.strftime('%Y-%m-%d'),
            'cantidad': cantidad,
            'precio_unitario': precio_unitario,
            'total': total,
            'metodo_pago': random.choice(['Tarjeta Crédito', 'Tarjeta Débito', 'Efectivo', 'Transferencia']),
            'estatus': random.choice(['Completada'] * 95 + ['Cancelada'] * 5)  # 95% completed
        })

    ventas = pd.DataFrame(sales_data)

    print(f">> Generated {len(sucursales)} branches")
    print(f">> Generated {len(lineas)} product categories")
    print(f">> Generated {len(sub_lineas)} subcategories")
    print(f">> Generated {len(productos)} products")
    print(f">> Generated {len(ventas)} sales transactions")

    return {
        'Sucursal': sucursales,
        'Linea': lineas,
        'Sub_Linea': sub_lineas,
        'Productos': productos,
        'Ventas': ventas
    }


def seed_duckdb():
    """
    Create and populate DuckDB database with sample data.

    Creates the analytical_cube.duckdb file in the data/ directory
    and populates it with synthetic sales data.
    """
    # Determine DuckDB file path
    project_root = Path(__file__).parent.parent
    data_dir = project_root / 'data'
    db_path = data_dir / 'analytical_cube.duckdb'

    # Ensure data directory exists
    data_dir.mkdir(exist_ok=True)

    print(f"\n{'='*70}")
    print("DuckDB Sample Data Generator")
    print(f"{'='*70}")
    print(f">> Target database: {db_path}")

    # Generate sample data
    tables = create_sample_data()

    # Connect to DuckDB
    print(f"\n>> Connecting to DuckDB...")
    conn = duckdb.connect(str(db_path))

    try:
        # Create schema if not exists
        conn.execute("CREATE SCHEMA IF NOT EXISTS sales_mart")
        print(">> Schema 'sales_mart' ready")

        # Drop existing tables (fresh start)
        for table_name in tables.keys():
            conn.execute(f"DROP TABLE IF EXISTS sales_mart.{table_name}")

        # Create and populate tables
        print("\n>> Creating tables and loading data...")
        for table_name, df in tables.items():
            # Create table from DataFrame
            conn.execute(f"CREATE TABLE sales_mart.{table_name} AS SELECT * FROM df")
            print(f"   ✓ {table_name}: {len(df)} rows")

        # Create indexes for better query performance
        print("\n>> Creating indexes for query optimization...")
        conn.execute("CREATE INDEX idx_ventas_fecha ON sales_mart.Ventas(fecha)")
        conn.execute("CREATE INDEX idx_ventas_producto ON sales_mart.Ventas(id_producto)")
        conn.execute("CREATE INDEX idx_ventas_sucursal ON sales_mart.Ventas(id_sucursal)")
        conn.execute("CREATE INDEX idx_productos_sublinea ON sales_mart.Productos(id_sub_linea)")
        conn.execute("CREATE INDEX idx_sublinea_linea ON sales_mart.Sub_Linea(id_linea)")
        print("   ✓ Indexes created successfully")

        # Verify data
        print("\n>> Verifying data integrity...")
        result = conn.execute("""
            SELECT
                COUNT(*) as total_sales,
                SUM(total) as total_revenue,
                COUNT(DISTINCT id_producto) as unique_products,
                COUNT(DISTINCT id_sucursal) as unique_branches
            FROM sales_mart.Ventas
            WHERE estatus = 'Completada'
        """).fetchone()

        print(f"\n{'='*70}")
        print("Database Summary:")
        print(f"{'='*70}")
        print(f"   Total Sales:        {result[0]:,}")
        print(f"   Total Revenue:      ${result[1]:,.2f}")
        print(f"   Unique Products:    {result[2]}")
        print(f"   Unique Branches:    {result[3]}")
        print(f"{'='*70}")

        print("\n✓ Sample data seeded successfully!")
        print(f"✓ Database location: {db_path}")
        print("\nYou can now start the application and view the dashboards.")

    except Exception as e:
        print(f"\n✗ Error seeding database: {str(e)}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    seed_duckdb()
