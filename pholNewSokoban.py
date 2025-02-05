import sys
import collections
import numpy as np
import heapq
import time
from newRender import Renderer
from board import BoardManager
import pygame
from renderSolution import renderSolution
import random
import numpy as np

class PriorityQueue:
    """Define a PriorityQueue data structure that will be used"""

    def __init__(self):
        self.Heap = []
        self.Count = 0
        self.Size=0

    def push(self, item, priority):
        entry = (priority, self.Count, item)
        heapq.heappush(self.Heap, entry)
        self.Count += 1
        self.Size+=1

    def pop(self):
        (_, _, item) = heapq.heappop(self.Heap)
        self.Size-=1
        return item

    def random_pop_from_top_n(self,n,popIndex):
        rank=[]
        for i in range(n):
            (heuristic, _, item) = heapq.heappop(self.Heap)
            self.Size-=1
            rank.append([item,heuristic])
        popped_element=rank.pop(popIndex)
        item=popped_element[0]
        heuristic=popped_element[1]
        for i in range(len(rank)):
            self.push(rank[i][0],rank[i][1])
        return item,heuristic
    def isEmpty(self):
        return len(self.Heap) == 0

class KQueue:
    """Define a PriorityQueue data structure that will be used"""

    def __init__(self):
        self.kQueue = []
        self.Count = 0

    def push(self, item, priority):
        entry = (priority, self.Count, item)
        self.kQueue.append(entry)
        self.Count += 1

    def pop(self):
        (priority, _, item) = self.kQueue.pop()
        return priority,item

    def isEmpty(self):
        return len(self.kQueue) == 0


"""Load puzzles and define the rules of sokoban"""


def transferToGameState(layout):
    """Transfer the layout of initial puzzle"""
    layout = [x.replace('\n', '') for x in layout]
    layout = [','.join(layout[i]) for i in range(len(layout))]
    layout = [x.split(',') for x in layout]
    maxColsNum = max([len(x) for x in layout])
    for irow in range(len(layout)):
        for icol in range(len(layout[irow])):
            if layout[irow][icol] == ' ':
                layout[irow][icol] = 0   # free space
            elif layout[irow][icol] == '#':
                layout[irow][icol] = 1  # wall
            elif layout[irow][icol] == '&':
                layout[irow][icol] = 2  # player
            elif layout[irow][icol] == 'B':
                layout[irow][icol] = 3  # box
            elif layout[irow][icol] == '.':
                layout[irow][icol] = 4  # goal
            elif layout[irow][icol] == 'X':
                layout[irow][icol] = 5  # box on goal
        colsNum = len(layout[irow])
        if colsNum < maxColsNum:
            layout[irow].extend([1 for _ in range(maxColsNum-colsNum)])
    return np.array(layout)


def PosOfPlayer(gameState):
    """Return the position of agent"""
    return tuple(np.argwhere(gameState == 2)[0])  # e.g. (2, 2)


def PosOfBoxes(gameState):
    """Return the positions of boxes"""
    return tuple(tuple(x) for x in np.argwhere((gameState == 3) | (gameState == 5)))  # e.g. ((2, 3), (3, 4), (4, 4), (6, 1), (6, 4), (6, 5))


def PosOfWalls(gameState):
    """Return the positions of walls"""
    return tuple(tuple(x) for x in np.argwhere(gameState == 1))  # e.g. like those above


def PosOfGoals(gameState):
    """Return the positions of goals"""
    return tuple(tuple(x) for x in np.argwhere((gameState == 4) | (gameState == 5)))  # e.g. like those above


def isEndState(posBox):
    """Check if all boxes are on the goals (i.e. pass the game)"""
    return sorted(posBox) == sorted(posGoals)


def isLegalAction(action, posPlayer, posBox):
    """Check if the given action is legal"""
    xPlayer, yPlayer = posPlayer
    if action[-1].isupper():  # the move was a push
        x1, y1 = xPlayer + 2 * action[0], yPlayer + 2 * action[1]
    else:
        x1, y1 = xPlayer + action[0], yPlayer + action[1]
    return (x1, y1) not in posBox + posWalls


def legalActions(posPlayer, posBox):
    """Return all legal actions for the agent in the current game state"""
    allActions = [[-1, 0, 'u', 'U'], [1, 0, 'd', 'D'],
                  [0, -1, 'l', 'L'], [0, 1, 'r', 'R']]
    xPlayer, yPlayer = posPlayer
    legalActions = []
    for action in allActions:
        x1, y1 = xPlayer + action[0], yPlayer + action[1]
        if (x1, y1) in posBox:  # the move was a push
            action.pop(2)  # drop the little letter
        else:
            action.pop(3)  # drop the upper letter
        if isLegalAction(action, posPlayer, posBox):
            legalActions.append(action)
        else:
            continue
    # e.g. ((0, -1, 'l'), (0, 1, 'R'))
    return tuple(tuple(x) for x in legalActions)


def updateState(posPlayer, posBox, action):
    """Return updated game state after an action is taken"""
    xPlayer, yPlayer = posPlayer  # the previous position of player
    newPosPlayer = [xPlayer + action[0], yPlayer +
                    action[1]]  # the current position of player
    posBox = [list(x) for x in posBox]
    if action[-1].isupper():  # if pushing, update the position of box
        posBox.remove(newPosPlayer)
        posBox.append([xPlayer + 2 * action[0], yPlayer + 2 * action[1]])
    posBox = tuple(tuple(x) for x in posBox)
    newPosPlayer = tuple(newPosPlayer)
    return newPosPlayer, posBox


def isFailed(posBox):
    """This function used to observe if the state is potentially failed, then prune the search"""
    rotatePattern = [[0, 1, 2, 3, 4, 5, 6, 7, 8],
                     [2, 5, 8, 1, 4, 7, 0, 3, 6],
                     [0, 1, 2, 3, 4, 5, 6, 7, 8][::-1],
                     [2, 5, 8, 1, 4, 7, 0, 3, 6][::-1]]
    flipPattern = [[2, 1, 0, 5, 4, 3, 8, 7, 6],
                   [0, 3, 6, 1, 4, 7, 2, 5, 8],
                   [2, 1, 0, 5, 4, 3, 8, 7, 6][::-1],
                   [0, 3, 6, 1, 4, 7, 2, 5, 8][::-1]]
    allPattern = rotatePattern + flipPattern

    for box in posBox:
        if box not in posGoals:
            board = [(box[0] - 1, box[1] - 1), (box[0] - 1, box[1]), (box[0] - 1, box[1] + 1),
                     (box[0], box[1] - 1), (box[0],
                                            box[1]), (box[0], box[1] + 1),
                     (box[0] + 1, box[1] - 1), (box[0] + 1, box[1]), (box[0] + 1, box[1] + 1)]
            for pattern in allPattern:
                newBoard = [board[i] for i in pattern]
                if newBoard[1] in posWalls and newBoard[5] in posWalls:
                    return True
                elif newBoard[1] in posBox and newBoard[2] in posWalls and newBoard[5] in posWalls:
                    return True
                elif newBoard[1] in posBox and newBoard[2] in posWalls and newBoard[5] in posBox:
                    return True
                elif newBoard[1] in posBox and newBoard[2] in posBox and newBoard[5] in posBox:
                    return True
                elif newBoard[1] in posBox and newBoard[6] in posBox and newBoard[2] in posWalls and newBoard[3] in posWalls and newBoard[8] in posWalls:
                    return True
    return False


"""Implement all approcahes"""


def breadthFirstSearch(isRender=False):
    """Implement breadthFirstSearch approach"""
    beginBox = PosOfBoxes(gameState)
    beginPlayer = PosOfPlayer(gameState)

    # e.g. ((2, 2), ((2, 3), (3, 4), (4, 4), (6, 1), (6, 4), (6, 5)))
    startState = (beginPlayer, beginBox)
    frontier = collections.deque([[startState]])  # store states
    actions = collections.deque([[0]])  # store actions
    exploredSet = set()
    while frontier:
        node = frontier.popleft()
        node_action = actions.popleft()
        if isEndState(node[-1][-1]):
            print(','.join(node_action[1:]).replace(',', ''))
            return node_action[1:]
        if node[-1] not in exploredSet:
            exploredSet.add(node[-1])
            for action in legalActions(node[-1][0], node[-1][1]):
                newPosPlayer, newPosBox = updateState(
                    node[-1][0], node[-1][1], action)
                if(isRender):
                    renderer.render(newPosPlayer, newPosBox)
                if isFailed(newPosBox):
                    continue
                frontier.append(node + [(newPosPlayer, newPosBox)])
                actions.append(node_action + [action[-1]])


def depthFirstSearch(isRender=False):
    """Implement depthFirstSearch approach"""
    beginBox = PosOfBoxes(gameState)
    beginPlayer = PosOfPlayer(gameState)

    startState = (beginPlayer, beginBox)
    frontier = collections.deque([[startState]])
    exploredSet = set()
    actions = [[0]]
    while frontier:
        node = frontier.pop()
        node_action = actions.pop()
        if isEndState(node[-1][-1]):
            print(','.join(node_action[1:]).replace(',', ''))
            return node_action[1:]
        if node[-1] not in exploredSet:
            exploredSet.add(node[-1])
            for action in legalActions(node[-1][0], node[-1][1]):
                newPosPlayer, newPosBox = updateState(
                    node[-1][0], node[-1][1], action)
                if(isRender):
                    renderer.render(newPosPlayer, newPosBox)
                if isFailed(newPosBox):
                    continue
                frontier.append(node + [(newPosPlayer, newPosBox)])
                actions.append(node_action + [action[-1]])


def heuristic(posPlayer, posBox):
    """A heuristic function to calculate the overall distance between the else boxes and the else goals"""
    distance = 0
    completes = set(posGoals) & set(posBox)
    sortposBox = list(set(posBox).difference(completes))
    sortposGoals = list(set(posGoals).difference(completes))
    for i in range(len(sortposBox)):
        distance += (abs(sortposBox[i][0] - sortposGoals[i][0])) + \
            (abs(sortposBox[i][1] - sortposGoals[i][1]))
    return distance


def cost(actions):
    """A cost function"""
    return len([x for x in actions if x.islower()])


def uniformCostSearch(isRender=False):
    """Implement uniformCostSearch approach"""
    beginBox = PosOfBoxes(gameState)
    beginPlayer = PosOfPlayer(gameState)

    startState = (beginPlayer, beginBox)
    frontier = PriorityQueue()
    frontier.push([startState], 0)
    exploredSet = set()
    actions = PriorityQueue()
    actions.push([0], 0)
    while frontier:
        node = frontier.pop()
        node_action = actions.pop()
        if isEndState(node[-1][-1]):
            print(','.join(node_action[1:]).replace(',', ''))
            return node_action[1:]
        if node[-1] not in exploredSet:
            exploredSet.add(node[-1])
            Cost = cost(node_action[1:])
            for action in legalActions(node[-1][0], node[-1][1]):
                newPosPlayer, newPosBox = updateState(
                    node[-1][0], node[-1][1], action)
                if(isRender):
                    renderer.render(newPosPlayer, newPosBox)
                if isFailed(newPosBox):
                    continue
                frontier.push(node + [(newPosPlayer, newPosBox)], Cost)
                actions.push(node_action + [action[-1]], Cost)


def aStarSearch(isRender=False):
    """Implement aStarSearch approach"""
    beginBox = PosOfBoxes(gameState)
    beginPlayer = PosOfPlayer(gameState)
    start_state = (beginPlayer, beginBox)
    frontier = PriorityQueue()
    frontier.push([start_state], heuristic(beginPlayer, beginBox))
    exploredSet = set()
    actions = PriorityQueue()
    actions.push([0], heuristic(beginPlayer, start_state[1]))
    while frontier:
        node = frontier.pop()
        node_action = actions.pop()
        if isEndState(node[-1][-1]):
            print(','.join(node_action[1:]).replace(',', ''))
            return node_action[1:]
        if node[-1] not in exploredSet:
            exploredSet.add(node[-1])
            Cost = cost(node_action[1:])
            for action in legalActions(node[-1][0], node[-1][1]):
                newPosPlayer, newPosBox = updateState(
                    node[-1][0], node[-1][1], action)
                if(isRender):
                    renderer.render(newPosPlayer, newPosBox)
                if isFailed(newPosBox):
                    continue
                Heuristic = heuristic(newPosPlayer, newPosBox)
                frontier.push(
                    node + [(newPosPlayer, newPosBox)], Heuristic + Cost)
                actions.push(node_action + [action[-1]], Heuristic + Cost)

# เหมือนกับ Astar แค่ลบ Cost ทิ้ง ตอนนี้เหมือนอมันจะติดลูป
def greedyBestFirstSearch(isRender=False):
    beginBox = PosOfBoxes(gameState)
    beginPlayer = PosOfPlayer(gameState)
    start_state = (beginPlayer, beginBox)
    frontier = PriorityQueue()
    frontier.push([start_state], heuristic(beginPlayer, beginBox))
    exploredSet = set()
    actions = PriorityQueue()
    actions.push([0], heuristic(beginPlayer, start_state[1]))
    while frontier:
        node = frontier.pop()
        node_action = actions.pop()
        if isEndState(node[-1][-1]):
            print(','.join(node_action[1:]).replace(',', ''))
            return node_action[1:]
        if node[-1] not in exploredSet:
            exploredSet.add(node[-1])
            for action in legalActions(node[-1][0], node[-1][1]):
                newPosPlayer, newPosBox = updateState(
                    node[-1][0], node[-1][1], action)
                if(isRender):
                    renderer.render(newPosPlayer, newPosBox)
                if isFailed(newPosBox):
                    continue
                Heuristic = heuristic(newPosPlayer, newPosBox)
                frontier.push(
                    node + [(newPosPlayer, newPosBox)], Heuristic )
                actions.push(node_action + [action[-1]], Heuristic )

def schedule(t):
    T_MAX=10*6
    return T_MAX*(0.98**t)

def greedyBestFirstSearchModified(isRender=False):
    beginBox = PosOfBoxes(gameState)
    beginPlayer = PosOfPlayer(gameState)
    start_state = (beginPlayer, beginBox)
    frontier = PriorityQueue()
    frontier.push([start_state], heuristic(beginPlayer, beginBox))
    exploredSet = set()
    actions = PriorityQueue()
    actions.push([0], heuristic(beginPlayer, start_state[1]))

    t=0
    prev_node_heuristic=1000000.0
    while frontier:

        # if(int(frontier.Size*0.3)<=0):
        #     n=1
        # else:
        #     n=int(frontier.Size*0.3)
        bound=10
        if(frontier.Size<=bound):
            n=frontier.Size
        else:
            n=bound

        # print(frontier.Size,n)
        randNum=random.randint(0,n-1)
        node,node_heuristic = frontier.random_pop_from_top_n(n,randNum)
        node_action, node_action_heuristic= actions.random_pop_from_top_n(n,randNum)
        if isEndState(node[-1][-1]):
            print(','.join(node_action[1:]).replace(',', ''))
            return node_action[1:]

        # T=schedule(t)
        # if T<0.1:
        #     T=0.1
        choice=[True,False]
        expand=False
        deltaE=node_heuristic-prev_node_heuristic
        if(deltaE>0.0):
            # prob=1/(2.7**(abs(deltaE/T)))
            # if prob<0.001:
            #     prob=0.001
            prob=0.001
            expand=np.random.choice(choice, 1,p = [prob,1-prob])[0]
        else:
            expand=True
        if(expand):
            if node[-1] not in exploredSet:
                exploredSet.add(node[-1])
                for action in legalActions(node[-1][0], node[-1][1]):
                    newPosPlayer, newPosBox = updateState(
                        node[-1][0], node[-1][1], action)
                    if(isRender):
                        renderer.render(newPosPlayer, newPosBox)
                    if isFailed(newPosBox):
                        continue
                    Heuristic = heuristic(newPosPlayer, newPosBox)
                    frontier.push(
                        node + [(newPosPlayer, newPosBox)], Heuristic )
                    actions.push(node_action + [action[-1]], Heuristic )
                prev_node_heuristic=node_heuristic
        else:
            frontier.push(node, node_heuristic)
            actions.push(node_action, node_action_heuristic)
        t+=1

def simulatedAnnealingSearch(isRender=False):
    beginBox = PosOfBoxes(gameState)
    beginPlayer = PosOfPlayer(gameState)
    start_state = (beginPlayer, beginBox)

    frontier = KQueue()
    frontier.push([start_state], heuristic(beginPlayer, beginBox))
    actions = KQueue()
    actions.push([0], heuristic(beginPlayer, start_state[1]))

    t=0
    while frontier:
        T=schedule(t)
        hValue,node = frontier.pop()
        hValue,node_action = actions.pop()
        if isEndState(node[-1][-1]):
                print(','.join(node_action[1:]).replace(',', ''))
                return node_action[1:]
        choice=[True,False]
        expand=True
        prevHValue=12
        deltaE=hValue-prevHValue
        prob=(1/(2.72**(deltaE/T)))
        # if(hValue>prevHValue):
        print(np.random.choice(choice, 1,p = [prob,1-prob]))

        # if(expand):
        #     legalActions=legalActions(node[-1][0], node[-1][1])
        #     listLegalActions=list(legalActions)
        #     random.shuffle(listLegalActions)
        #     shuffledTupLegalActions = tuple(listLegalActions)
        #     for action in shuffledTupLegalActions :

        #         newPosPlayer, newPosBox = updateState(
        #             node[-1][0], node[-1][1], action)
        #         if(isRender):
        #             renderer.render(newPosPlayer, newPosBox)
        #         if isFailed(newPosBox):
        #             continue
        #         Heuristic = heuristic(newPosPlayer, newPosBox)
        #         frontier.push(
        #                 node + [(newPosPlayer, newPosBox)], Heuristic)
            
        #         actions.push(node_action + [action[-1]], Heuristic)
        # prevHValue,prevNode =hValue,node
        # t+=1



# def best_first_search(actual_Src, target, n):
#     visited = [False] * n
#     pq = PriorityQueue()
#     pq.put((0, actual_Src))
#     visited[actual_Src] = True
     
#     while pq.empty() == False:
#         u = pq.get()[1]
#         # Displaying the path having lowest cost
#         print(u, end=" ")
#         if u == target:
#             break
 
#         for v, c in graph[u]:
#             if visited[v] == False:
#                 visited[v] = True
#                 pq.put((c, v))
#     print()

# // Pseudocode for Best First Search
# Best-First-Search(Graph g, Node start)
#     1) Create an empty PriorityQueue
#        PriorityQueue pq;
#     2) Insert "start" in pq.
#        pq.insert(start)
#     3) Until PriorityQueue is empty
#           u = PriorityQueue.DeleteMin
#           If u is the goal
#              Exit
#           Else
#              Foreach neighbor v of u
#                 If v "Unvisited"
#                     Mark v "Visited"                    
#                     pq.insert(v)
#              Mark u "Examined"                    
# End procedure
"""Read command"""


def readCommand(argv):
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option('-l', '--level', dest='sokobanLevels',
                      help='level of game to play', default='level1.txt')
    parser.add_option('-m', '--method', dest='agentMethod',
                      help='research method', default='bfs')
    parser.add_option('-r', '--render', dest='render', action="store_true",
                      help='render searching with pygame', default=False)
    args = dict()
    options, _ = parser.parse_args(argv)
    with open('sokobanLevels/'+options.sokobanLevels, "r") as f:
        layout = f.readlines()
    args['layout'] = layout
    args['method'] = options.agentMethod
    args['isRender'] = options.render
    return args


if __name__ == '__main__':
    
    time_start = time.time()
    layout, method, isRender = readCommand(sys.argv[1:]).values()
    gameState = transferToGameState(layout)
    posWalls = PosOfWalls(gameState)
    posGoals = PosOfGoals(gameState)
    solution = []

    if(isRender): renderer = Renderer(gameState)
    
    if method == 'astar':
        solution = aStarSearch(isRender)
    elif method == 'dfs':
        solution = depthFirstSearch(isRender)
    elif method == 'bfs':
        solution = breadthFirstSearch(isRender)
    elif method == 'ucs':
        solution = uniformCostSearch(isRender)
    elif method == 'gbfs':
        solution = greedyBestFirstSearchModified(isRender)
    else:
        raise ValueError('Invalid method.')
    time_end = time.time()
    print('Runtime of %s: %.2f second.' % (method, time_end-time_start))
    if(isRender):
        renderSolution(layout, solution)
