"""Offline reference algorithms for the archive's output practice cases.

These functions only run while rebuilding/verifying the answer key. Participant
code is never imported or executed by the web application.
"""
from collections import Counter
from heapq import heappop, heappush
from itertools import combinations


def partition_work(values, workers):
    low, high = max(values), sum(values)
    while low < high:
        limit = (low + high) // 2
        groups, total = 1, 0
        for value in values:
            if total + value > limit:
                groups += 1
                total = 0
            total += value
        if groups <= workers:
            high = limit
        else:
            low = limit + 1
    return low


def battle_winner(signal, size):
    assert len(signal) % size == 0
    wins = Counter()
    for start in range(0, len(signal), size):
        counts = Counter(signal[start:start + size])
        wins[min(counts, key=lambda c: (-counts[c], c))] += 1
    return min(wins, key=lambda c: (-wins[c], c))


def burgers(hours, shipments, lifetime):
    # One shipment supplies one burger. Choose the maximum-weight matching
    # between shipments and eligible hours (greedy weighted transversal matroid).
    slots = {}

    def assign(index, seen):
        arrival, _ = shipments[index]
        for hour in range(arrival, min(hours + 1, arrival + lifetime)):
            if hour in seen:
                continue
            seen.add(hour)
            if hour not in slots or assign(slots[hour], seen):
                slots[hour] = index
                return True
        return False

    total = 0
    for index in sorted(range(len(shipments)), key=lambda i: -shipments[i][1]):
        if assign(index, set()):
            total += shipments[index][1]
    return total


def minimum_energy_core(energy, requirements):
    def matches(wanted):
        j = 0
        for value in energy:
            if j < len(wanted) and value >= wanted[j]:
                j += 1
        return j == len(wanted)
    if matches(requirements):
        return 0
    candidates = [value for i, value in enumerate(requirements)
                  if matches(requirements[:i] + requirements[i + 1:])]
    return min(candidates, default=-1)


def merge_stalls(values):
    n = len(values)
    dp = [[0] * n for _ in range(n)]
    answer = max(values)
    for i, value in enumerate(values):
        dp[i][i] = value
    for size in range(2, n + 1):
        for start in range(n - size + 1):
            end = start + size - 1
            for split in range(start, end):
                if dp[start][split] and dp[start][split] == dp[split + 1][end]:
                    dp[start][end] = max(dp[start][end], dp[start][split] + 1)
            answer = max(answer, dp[start][end])
    return answer


def enclosure_saving(points):
    def area(group):
        return ((max(x for x, _ in group) - min(x for x, _ in group)) *
                (max(y for _, y in group) - min(y for _, y in group)))
    original = area(points)
    best = original
    for axis in (0, 1):
        ordered = sorted(points, key=lambda p: p[axis])
        for i in range(1, len(ordered)):
            if ordered[i - 1][axis] < ordered[i][axis]:
                best = min(best, area(ordered[:i]) + area(ordered[i:]))
    return original - best


def consistent_pairs(rankings):
    return sum(all(row.index(a) < row.index(b) for row in rankings)
               for a, b in combinations(rankings[0], 2))


def balanced_sectors(points):
    best = len(points)
    for a in {0} | {x + 1 for x, _ in points}:
        for b in {0} | {y + 1 for _, y in points}:
            counts = Counter((x > a, y > b) for x, y in points)
            best = min(best, max(counts.values()))
    return best


def equal_zone_merges(values):
    total = sum(values)
    if total == 0:
        return 0
    for count in range(len(values), 0, -1):
        if total % count:
            continue
        target, running, groups = total // count, 0, 0
        for value in values:
            running += value
            if running > target:
                break
            if running == target:
                groups += 1
                running = 0
        else:
            if running == 0 and groups == count:
                return len(values) - count


def grid_energy(grid):
    assert grid and len({len(row) for row in grid}) == 1
    start = next((r, c) for r, row in enumerate(grid) for c, v in enumerate(row) if v == 'S')
    energy = lambda value: int(value) if value.isdigit() else 0
    distance = {start: 0}
    heap = [(0, *start)]
    while heap:
        cost, r, c = heappop(heap)
        if cost != distance[(r, c)]:
            continue
        if grid[r][c] == 'T':
            return cost
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if not (0 <= nr < len(grid) and 0 <= nc < len(grid[0])) or grid[nr][nc] == '#':
                continue
            candidate = cost + 1 + (energy(grid[r][c]) - energy(grid[nr][nc])) ** 2
            if candidate < distance.get((nr, nc), float('inf')):
                distance[nr, nc] = candidate
                heappush(heap, (candidate, nr, nc))
    return -1


def laser_cost_small(initial, k, x, y, z):
    """Exact shortest path for SMALL practice cases, not a contest-scale solver.

    Use the printed Lumina formula literally; disallow negative health.
    Bound states by initial max health (none of the operations can increase it).
    """
    initial = tuple(initial)
    distance, heap = {initial: 0}, [(0, initial)]
    while heap:
        cost, state = heappop(heap)
        if distance[state] != cost:
            continue
        if not any(state):
            return cost
        candidates = []
        for i, value in enumerate(state):
            if value:
                new = list(state)
                new[i] -= 1
                candidates.append((new, y))
        for i in range(len(state) - k + 1):
            if all(state[j] > 0 for j in range(i, i + k)):
                new = list(state)
                for j in range(i, i + k):
                    new[j] -= 1
                candidates.append((new, x))
        for i in range(1, len(state) - 1):
            new = list(state)
            new[i] = max(state[i - 1] - 1, state[i], state[i + 1]) - 1
            if new[i] >= 0:
                candidates.append((new, z))
        for new, extra in candidates:
            key, proposed = tuple(new), cost + extra
            if proposed < distance.get(key, float('inf')):
                distance[key] = proposed
                heappush(heap, (proposed, key))


def traffic_bounds(segments):
    def walk(rows):
        low, high = 0, 10 ** 12
        for kind, a, b in rows:
            if kind == 'none':
                low, high = max(low, a), min(high, b)
            elif kind == 'on':
                low, high = low + a, high + b
            else:
                low, high = max(0, low - b), high - a
            assert 0 <= low <= high
        return low, high
    inverse = [('off' if kind == 'on' else 'on' if kind == 'off' else 'none', a, b)
               for kind, a, b in reversed(segments)]
    return walk(inverse), walk(segments)
