import math
from collections import deque

def calculate_distance(pos1, pos2):
    return math.dist(pos1, pos2)

def build_galaxy_graph(stars, max_reach_ly):
    """
    Costruisce la rete di connettività spaziale universale:
    collega ogni stella a tutte le stelle vicine entro max_reach_ly.
    """
    galaxy_graph = {s['id']: [] for s in stars}
    connection_count = 0

    for i in range(len(stars)):
        s1 = stars[i]
        for j in range(i + 1, len(stars)):
            s2 = stars[j]
            dist = calculate_distance(s1['position'], s2['position'])
            if 0 < dist <= max_reach_ly:
                galaxy_graph[s1['id']].append(s2['id'])
                galaxy_graph[s2['id']].append(s1['id'])
                connection_count += 1

    print(f"[PATHFINDING] Rete galattica universale creata: {connection_count} rotte possibili tra {len(stars)} sistemi.")
    return galaxy_graph

def find_bfs_path(graph, start_id, target_id):
    """Trova il percorso a tappe minimo tra due sistemi nel grafo."""
    if start_id == target_id:
        return [start_id]
    queue = deque([[start_id]])
    visited = {start_id}

    while queue:
        path = queue.popleft()
        node = path[-1]
        if node == target_id:
            return path
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])
    return []