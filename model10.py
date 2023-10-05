import pandas as pd


def convert(seconds):
  min, sec = divmod(seconds, 60)
  hour, min = divmod(min, 60)
  return('%d:%02d:%02d'%(hour,min,sec))

NodesFile, EdgesFile = dir+'Nodes.csv', dir+'Edges.csv'
#NodesFile, EdgesFile = dir+'Nodes.csv', dir+'Edges-50-50.csv'
Nodes_df = pd.read_csv(NodesFile)
Edges_df = pd.read_csv(EdgesFile)

# Sets
lookupNodes = {nrow['ID']:(i, nrow['Name'], nrow['Type'], nrow['Min'], nrow['Max'], nrow['Volume']) for i, nrow in Nodes_df.iterrows()}
N = lookupNodes.keys() # Get a list of nodes
print(N)
print(lookupNodes)

lookupEdges = {erow['ID']:(i, erow['Name'], erow['FromNode'], erow['ToNode'], erow['PumpID'], erow['PumpCap'], erow['Note'], erow['Used'], erow['Ratio'], erow['Symbol_input']) \
               for i, erow in Edges_df.iterrows()}
E = lookupEdges.keys() # Get a list of edges

# Derived sets
ToN = {n2:[e for e in E if lookupEdges[e][3]==n2] for n2 in N}
NOut = {n1:[e for e in E if lookupEdges[e][2]==n1] for n1 in N}
SN = [n for n in N if lookupNodes[n][2] == 'Intermediate']
SO = [n for n in N if lookupNodes[n][2] == 'Source']
SD = [n for n in N if lookupNodes[n][2] == 'Sink']

# Import pyomo
from pyomo.environ import *

# Create a model object
m = ConcreteModel('Water management model')

# Decision variables
m.S = Var(N, domain=NonNegativeReals)
m.VL = Var(E, domain=NonNegativeReals)

m.obj = Objective(expr=sum(m.VL[e]/lookupEdges[e][5] for e in E if lookupEdges[e][5] > 0), sense=minimize)

# Balance water volume at the intermediate node
m.IntermediateEq = ConstraintList()
for inode in SN:
  m.IntermediateEq.add(expr=sum(m.VL[ein] for ein in ToN[inode] if lookupEdges[ein][7] == 1) + lookupNodes[inode][5] == m.S[inode] \
                       + sum(m.VL[eout] for eout in NOut[inode] if lookupEdges[eout][7] == 1) )
                       
# Min/Max constraint at the intermediate node
m.MinMaxEq = ConstraintList()
for inode in SN:
  m.MinMaxEq.add(expr=m.S[inode] >= lookupNodes[inode][3])
  m.MinMaxEq.add(expr=m.S[inode] <= lookupNodes[inode][4])                       
                       
# Sum to sink node
m.SumSinkEq = ConstraintList()
for knode in SD:
  m.SumSinkEq.add(expr=m.S[knode] == sum(m.VL[e] for e in ToN[knode] if lookupEdges[e][7] == 1))                       

# Sink node requirement
m.SinkEq = ConstraintList()
for knode in SD:
  if lookupNodes[knode][5] >= 0:
    m.SinkEq.add(expr=m.S[knode] == lookupNodes[knode][5])

# Source node requirement
m.SourceEq = ConstraintList()
for jnode in SO:
  if lookupNodes[jnode][5] >= 0:
    for e in NOut[jnode]:
      if lookupEdges[e][7] == 1:
        m.SourceEq.add(expr=m.VL[e] == lookupEdges[e][8]*lookupNodes[jnode][5])

# Determine the solution
SolverFactory('cbc').solve(m).write()

# Report the result
print('The optimal volume is ', m.obj())

# The remaining water in the intermediate node
for inode in SN:
  print('Remaining water (m^3) in = ', inode, ' is ', m.S[inode]())

OEdge_ID = list(lookupEdges.keys())
OEdge_Name = [lookupEdges[erow][1] for erow in lookupEdges.keys()]
OEdge_FromNode =  [lookupEdges[erow][2] for erow in lookupEdges.keys()]
OEdge_ToNode =  [lookupEdges[erow][3] for erow in lookupEdges.keys()]
OEdge_PumpID =  [lookupEdges[erow][4] for erow in lookupEdges.keys()]
OEdge_WaterLevel, OEdge_PumpTime = [], []
for e in E:
    if m.VL[e]() > 0:
      OEdge_WaterLevel.append(m.VL[e]())
      OEdge_PumpTime.append(convert(m.VL[e]()/lookupEdges[e][5]))
    #Case of no flow but pump installed
    else:
      OEdge_WaterLevel.append(0)
      OEdge_PumpTime.append(convert(0))
zipped = list(zip(OEdge_ID,OEdge_Name,OEdge_FromNode,OEdge_ToNode,OEdge_PumpID,OEdge_WaterLevel,OEdge_PumpTime))
OEdge_df = pd.DataFrame(zipped, columns=['ID', 'Name', 'FromNode',
                        'ToNode', 'PumpID/Gate/Flow','Flow Volume (m^3)','PumpTime'])
# Dump to CSV/Excel
OEdge_df.to_csv(dir+'OutputEdges.csv')
OEdge_df.to_excel(dir+'OutputEdges.xlsx')

# Storage output

OStorage_NodeID = list(lookupNodes.keys())
Initial_Storage = [lookupNodes[inode][5] for inode in N]
Max_Storage = [lookupNodes[inode][4] for inode in N]
OStorage_VarDescription = [lookupNodes[inode][1] for inode in N]
OStorage_Value = [m.S[inode]() for inode in N]
zipped = list(zip(OStorage_NodeID, Initial_Storage, Max_Storage,OStorage_VarDescription, OStorage_Value))
OStorage_df = pd.DataFrame(zipped, columns=['NodeID','Initial Storage', 'Max Storage' ,'Description', 'Final Storage (m^3)'])

# Dump to CSV/Excel
OStorage_df.to_csv(dir+'Storage.csv')
OStorage_df.to_excel(dir+'Storage.xlsx')


















                       
                       
                       
                       
                       
                       

