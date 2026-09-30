from hyperdb import HypergraphDB
import os

class DatabaseManager:
    """Database manager supporting multiple database instances."""
    def __init__(self):
        self.databases = {}
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        root_cache = os.path.join(repo_root, "hyperrag_cache")
        self.cache_dir = root_cache if os.path.exists(root_cache) else "hyperrag_cache"
        
    def get_database(self, database_name=None):
        """Get database instance by name."""
        if database_name is None:
            return None
            
        # Build complete database file path
        database_path = os.path.join(self.cache_dir, database_name, "hypergraph_chunk_entity_relation.hgdb")
        
        # Check if database file exists
        if not os.path.exists(database_path):
            raise Exception(f"Database file '{database_path}' does not exist")
            
        # Create new instance if not already cached
        if database_name not in self.databases:
            self.databases[database_name] = HypergraphDB(storage_file=database_path)
            
        return self.databases[database_name]
    
    def list_databases(self):
        """List all available database directories in hyperrag_cache."""
        databases = []
        
        # Check if hyperrag_cache directory exists
        if not os.path.exists(self.cache_dir):
            return databases
        
        try:
            for file in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, file)
               
                if os.path.isdir(file_path):
                    databases.append(file)
        except OSError:
            pass
                
        return databases

# Global database manager instance
db_manager = DatabaseManager()

# Legacy hg variable for backward compatibility
hg = db_manager.get_database()

def get_hypergraph(database=None):
    """Get full hypergraph details for the specified database."""
    db = db_manager.get_database(database)
    all_v = db.all_v
    all_e = db.all_e

    return get_all_detail(all_v, all_e, database)

def get_vertices(database=None, page=None, page_size=None):
    """Get vertices list with optional pagination."""
    db = db_manager.get_database(database)
    all_v = list(db.all_v)
    
    if page is None or page_size is None:
        return all_v
    
    total = len(all_v)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    page_data = all_v[start_idx:end_idx]
    
    return {
        'data': page_data,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size
    }

def getFrequentVertices(database=None, page=None, page_size=None):
    """Get frequent vertices with incident edges, supporting pagination."""
    db = db_manager.get_database(database)
    
    # Extract vertices appearing two or more times in hyperedges
    frequent_vertices = {}
    for e in db.all_e:
        for v in e:
            if v in frequent_vertices:
                frequent_vertices[v] += 1
            else:
                frequent_vertices[v] = 1
    
    frequent_vertices = [v for v, count in frequent_vertices.items() if count >= 2]

    if page is None or page_size is None:
        return frequent_vertices

    total = len(frequent_vertices)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    page_data = frequent_vertices[start_idx:end_idx]

    return {
        'data': page_data,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size
    }

def get_vertice(vertex_id: str, database=None):
    """Get specified vertex JSON."""
    db = db_manager.get_database(database)
    vertex = db.v(vertex_id)
    return vertex

def get_hyperedges(database=None, page=None, page_size=None):
    """Get hyperedges list with details."""
    db = db_manager.get_database(database)
    all_e = list(db.all_e)

    hyperedges = []
    for e in all_e:
        hyperedge_id = '|*|'.join(e)
        hyperedge_data = db.e(e)
        
        edge_info = {
            'id': hyperedge_id,
            'vertices': list(e),
            'keywords': hyperedge_data.get('keywords', ''),
            'summary': hyperedge_data.get('summary', ''),
            'description': hyperedge_data.get('keywords', '')
        }
        hyperedges.append(edge_info)

    if page is None or page_size is None:
        return hyperedges
    
    total = len(hyperedges)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    page_data = hyperedges[start_idx:end_idx]
    
    return {
        'data': page_data,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size
    }

def get_hyperedge(hyperedge_id: str, database=None):
    """Get specified hyperedge JSON."""
    db = db_manager.get_database(database)
    hyperedge = db.e(hyperedge_id)
    return hyperedge

def get_hyperedge_detail(vertices: list, database=None):
    """Get details for a specified hyperedge."""
    try:
        db = db_manager.get_database(database)
        edge_tuple = db.encode_e(tuple(vertices))
        
        if not db.has_e(edge_tuple):
            raise Exception("Hyperedge does not exist")
        
        hyperedge_data = db.e(edge_tuple)
        return hyperedge_data
    except Exception as e:
        raise Exception(f"Failed to get hyperedge detail: {str(e)}")

def get_vertice_neighbor_inner(vertex_id: str, database=None):
    """Get neighbors of a specified vertex."""
    try:
        db = db_manager.get_database(database)
        n = db.nbr_v(vertex_id)
        n.add(vertex_id)
        e = db.nbr_e_of_v(vertex_id)
    except Exception:
        n = []
        e = []

    return (n, e)

def get_vertice_neighbor(vertex_id: str, database=None):
    """Get vertex neighborhood graph details."""
    n, e = get_vertice_neighbor_inner(vertex_id, database)
    return get_all_detail(n, e, database)

def get_all_detail(all_v, all_e, database=None):
    """Get node and hyperedge dictionary details."""
    db = db_manager.get_database(database)
    nodes = {}
    for v in all_v:
        nodes[v] = db.v(v)

    hyperedges = {}
    for e in all_e:
        data = db.e(e)
        data['keywords'] = data['keywords'].replace("<SEP>", ",")
        hyperedges['|#|'.join(e)] = data

    return {"vertices": nodes, "edges": hyperedges}

def get_hyperedge_neighbor_server(hyperedge_id: str, database=None):
    """Get neighbors of a specified hyperedge."""
    nodes = hyperedge_id.split("|#|")
    vertices = set()
    hyperedges = set()
    for node in nodes:
        n, e = get_vertice_neighbor_inner(node, database)
        vertices.update(n)
        hyperedges.update(e)

    return get_all_detail(vertices, hyperedges, database)

def add_vertex(vertex_id: str, vertex_data: dict, database=None):
    """Add a new vertex."""
    try:
        db = db_manager.get_database(database)
        if db.has_v(vertex_id):
            raise Exception(f"Vertex '{vertex_id}' already exists")
        
        db.add_v(vertex_id, vertex_data)
        db.save(db.storage_file)
        db._clear_cache()
        
        return db.v(vertex_id)
    except Exception as e:
        raise Exception(f"Failed to add vertex: {str(e)}")

def add_hyperedge(vertices: list, hyperedge_data: dict, database=None):
    """Add a new hyperedge."""
    try:
        db = db_manager.get_database(database)
        for vertex in vertices:
            if not db.has_v(vertex):
                raise Exception(f"Vertex '{vertex}' does not exist")
        
        edge_tuple = db.encode_e(tuple(vertices))
        
        if db.has_e(edge_tuple):
            raise Exception("Hyperedge already exists")
        
        db.add_e(edge_tuple, hyperedge_data)
        db.save(db.storage_file)
        db._clear_cache()
        
        return db.e(edge_tuple)
    except Exception as e:
        raise Exception(f"Failed to add hyperedge: {str(e)}")

def update_vertex(vertex_id: str, vertex_data: dict, database=None):
    """Update vertex information."""
    try:
        db = db_manager.get_database(database)
        if not db.has_v(vertex_id):
            raise Exception(f"Vertex '{vertex_id}' does not exist")
        
        existing_data = db.v(vertex_id)
        for key, value in vertex_data.items():
            if value:
                existing_data[key] = value
        
        db.remove_v(vertex_id)
        db.add_v(vertex_id, existing_data)
        db.save(db.storage_file)
        db._clear_cache()
        
        return db.v(vertex_id)
    except Exception as e:
        raise Exception(f"Failed to update vertex: {str(e)}")

def update_hyperedge(vertices: list, hyperedge_data: dict, database=None):
    """Update hyperedge information."""
    try:
        db = db_manager.get_database(database)
        edge_tuple = db.encode_e(tuple(vertices))
        
        if not db.has_e(edge_tuple):
            raise Exception("Hyperedge does not exist")
        
        existing_data = db.e(edge_tuple)
        for key, value in hyperedge_data.items():
            if value:
                existing_data[key] = value
        
        db.remove_e(edge_tuple)
        db.add_e(edge_tuple, existing_data)
        db.save(db.storage_file)
        db._clear_cache()
        
        return db.e(edge_tuple)
    except Exception as e:
        raise Exception(f"Failed to update hyperedge: {str(e)}")

def delete_vertex(vertex_id: str, database=None):
    """Delete a vertex."""
    try:
        db = db_manager.get_database(database)
        if not db.has_v(vertex_id):
            raise Exception(f"Vertex '{vertex_id}' does not exist")
        
        db.remove_v(vertex_id)
        db.save(db.storage_file)
        db._clear_cache()
        
        return True
    except Exception as e:
        raise Exception(f"Failed to delete vertex: {str(e)}")

def delete_hyperedge(vertices: list, database=None):
    """Delete a hyperedge."""
    try:
        db = db_manager.get_database(database)
        edge_tuple = db.encode_e(tuple(vertices))
        
        if not db.has_e(edge_tuple):
            raise Exception("Hyperedge does not exist")
        
        db.remove_e(edge_tuple)
        db.save(db.storage_file)
        db._clear_cache()
        
        return True
    except Exception as e:
        raise Exception(f"Failed to delete hyperedge: {str(e)}")