from numpy import *
from .variables import *
from .model_part import *
import json

class GidIO:
    def __init__(self, outputfilename,zero_based_indices_for_nodes=False):
        
        try:              
            self.project_parameters = json.loads(open('ProjectParameters.json').read())
            inputfilename = self.project_parameters["solver_settings"] ["model_import_settings"]["input_filename"]
            inputfiletype = self.project_parameters["solver_settings"] ["model_import_settings"]["input_type"]
            self.input_file = open( inputfilename+'.'+inputfiletype ) 
            self.submodel_list = self.project_parameters["solver_settings"] ["processes_sub_model_part_list"]
            self.constraints_process_list= self.project_parameters["constraints_process_list"]
            self.loads_process_list= self.project_parameters["loads_process_list"]
        except:
            self.input_file = 0
            print("inputfile not found")
        
        self.mesh_file = open( outputfilename + ".post.msh", 'w')
        self.result_file = open( outputfilename + ".post.res", 'w')
        self.result_file.write("GiD Post Results File 1.0\n")
        self.zero_based_indices_for_nodes = zero_based_indices_for_nodes
        
    def ReadModelPart(self, model_part):
        if self.input_file:            
            for line in self.input_file:
                if line.find("Begin") != -1:
                    words = self.ReadWords(line)
                    print(words[1])
                    if words[1] == "Properties":
                        id = int(words[2])
                        if id not in model_part.Properties:
                            model_part.AddProperties({id:{}})
                        self.ReadProperties(model_part.Properties[id])
                        print(model_part.Properties)
                    elif words[1] == "Nodes":
                        self.ReadNodes(model_part)
                    elif words[1] == "Elements":
                        self.ReadElements(words[2],model_part)
                    elif words[1] == "Conditions":
                        self.ReadConditions(words[2],model_part)
                    elif words[1] == "NodalData":
                        self.ReadNodalData(words[2])
                    elif words[1] == "SubModelPart" and words[len(words)-1].find("DISPLACEMENT")!=-1:
                        contraint_name = words[len(words)-1]
                        self.ReadContraint(contraint_name,model_part)
                    elif words[1] == "SubModelPart" and words[len(words)-1].find("PointLoad3D")!=-1:
                        load_name = words[len(words)-1]
                        self.ReadPointLoad(load_name,model_part)





     
                        
    def ReadWords(self,line):
        i  = line.find("//")
        if i != -1:
            return line[:i].split() 
        return line.split() 
         
    def ReadProperties(self,properties):
        for line in self.input_file:
            if line.find("End") == -1:
                words = self.ReadWords(line)
                if words[1].find("[") ==-1: #scalar case
                    variable,value = words[0],float(words[1])
                    if variable not in properties:
                        properties.update({variable:value})
                    else:
                        properties[variable] = value
            else:
                break
                
    def ReadNodes(self,model_part):
        counter = 0
        for line in self.input_file:
            if line.find("End") == -1:
                counter += 1
                words = self.ReadWords(line)
                id = int(words[0])
                coordinates = [float(words[1]), float(words[2]), float(words[3])]
                model_part.AddNode(id, coordinates)
                if counter < 10:
                    print(model_part.Nodes[id])
            else:
                break
        print(counter)
                   
    def ReadElements(self,element_name, model_part):
        element_type = __import__(element_name)
        counter = 0
        for line in self.input_file:
            if line.find("End") == -1:
                counter += 1
                words = self.ReadWords(line)
                print (words)
                id,properties_id, connectivity = int(words[0]),  int(words[1]), [int(x) for  x in words[2:]]
                properties = model_part.Properties[properties_id]
                print(properties)
                element_nodes = []
                for i in connectivity:
                    if i not in model_part.Nodes:
                        print("Warning: node #{} not found".format(i))
                    element_nodes.append(model_part.Nodes[i])
                
                element = element_type.Create(id, properties, element_nodes)
                model_part.Elements.update({id:element})
                if counter < 10:
                    print(id, ":", properties, ",", connectivity)
            else:
                break
        print(counter)
                   
    def ReadConditions(self,condition_type,model_part):
        print(condition_type)
        condition_connectivities = {}    
        counter = 0
        for line in self.input_file:
            if line.find("End") == -1:
                counter += 1
                words = self.ReadWords(line)
                id,properties, connectivity = int(words[0]),  int(words[1]), [int(x) for  x in words[2:]]
                new={id: [properties,connectivity]}
                condition_connectivities.update(new)
                if counter < 10:
                    print(id, ":", properties, ",", connectivity)                    
            else:
                break
        print(counter)        
        model_part.AddConditions("point_condition_2d", condition_connectivities)
                   
    def ReadNodalData(self,variable): ##nicht mehr benötigt
        print(variable)
        counter = 0
        for line in self.input_file:
            if line.find("End") == -1:
                counter += 1
                words = self.ReadWords(line)
                if len(words) >= 3:
                    id,value = int(words[0]),  float(words[2])
                    if counter < 10:
                        print(id, ":", value)
            else:
                break
        print(counter)
        
    def ReadContraint(self,constraint_name,model_part):
        print(constraint_name)
        knoten = []
        for line in self.input_file:
            if line.find("Begin SubModelPartNodes") != -1:
                for line in self.input_file:
                    if line.find("End") == -1:
                        words = self.ReadWords(line)
                        knoten.append(int(words[0]))                        
                    else:
                        break
            else:
                break
        n = len(knoten)
        print(n)
        print(knoten)
        
        for key in self.constraints_process_list:
            model_part_name = key["Parameters"]["model_part_name"]
            constraint_value = key["Parameters"]["value"]

            if constraint_name == model_part_name:
                for node_i in range(0,n):
                    node = model_part.Nodes[knoten[node_i]]
                    if constraint_value[0] == 0.0:
                        node.SetSolutionStepValue("DISPLACEMENT_X", 0, 0.0)
                        node.Fix("DISPLACEMENT_X")
                    if constraint_value[1] == 0.0:
                        node.Fix("DISPLACEMENT_Y")
                        node.SetSolutionStepValue("DISPLACEMENT_Y", 0, 0.0)




    def ReadPointLoad(self,load_name_mdpa,model_part):      
        
        print(load_name_mdpa)
        knoten = []
        for line in self.input_file:
            if line.find("Begin SubModelPartNodes") != -1:
                for line in self.input_file:
                    if line.find("End") == -1:
                        words = self.ReadWords(line)
                        knoten.append(int(words[0]))                        
                    else:
                        break
            else:
                break
        n = len(knoten)
        print(n)
        print(knoten)
        
        for key in self.loads_process_list:
            load_name = key["Parameters"]["model_part_name"]
            load_modulus = key["Parameters"]["modulus"]
            load_direction = key["Parameters"]["direction"]            

            if load_name_mdpa == load_name:
                for node_i in range(0,n):
                    node = model_part.Nodes[ knoten [node_i] ]
                    if load_direction[0] != 0.0:
                        node.SetSolutionStepValue("EXTERNAL_FORCE_X", 0,load_modulus*load_direction[0])
                        node.Fix("EXTERNAL_FORCE_X")
                    if load_direction[1] != 0.0:
                        node.Fix("EXTERNAL_FORCE_Y")
                        node.SetSolutionStepValue("EXTERNAL_FORCE_Y", 0,load_modulus*load_direction[1])
         
                
        
    def gid_id( self, kratos_id ):
        if self.zero_based_indices_for_nodes:
            return kratos_id+1
        else:
            return kratos_id
        
    def WriteMesh(self,model_part, mesh_name):
            self.mesh_file.write("MESH \"")
            self.mesh_file.write(mesh_name)
            self.mesh_file.write("\" dimension 3 ElemType Linear Nnode 2\n")
            self.mesh_file.write("Coordinates\n")
            if 0 in model_part.Nodes:
                self.zero_based_indices_for_nodes = True
            for node in model_part.NodeIterators():
                if(len(node.coordinates) == 3):
                    self.mesh_file.write("{} {} {} {}\n".format(self.gid_id(node.Id), node.coordinates[0], node.coordinates[1], node.coordinates[2]))
                else:
                    self.mesh_file.write("{} {} {} {}\n".format( self.gid_id(node.Id) , node.coordinates[0], node.coordinates[1], 0.0))
            self.mesh_file.write("end coordinates\n")
            self.mesh_file.write("Elements\n")   
            for element in model_part.ElementIterators():
                if(element.geometry.GetNumberOfNodes() == 3):
                    self.mesh_file.write("{} {} {} {}\n".format(self.gid_id(element.Id), self.gid_id(element.geometry[0].Id), self.gid_id(element.geometry[1].Id), self.gid_id(element.geometry[2].Id) ))
                else:
                    self.mesh_file.write("{} {} {} {}\n".format(self.gid_id(element.Id), self.gid_id(element.geometry[0].Id), self.gid_id(element.geometry[1].Id), 0.0))
            self.mesh_file.write("end elements\n")
            self.mesh_file.flush()

    def WriteNodalResults(self, variable, nodes, time):
        if isinstance(variable, list):
            self.result_file.write("Result \"")
            self.result_file.write(variable[0])
            self.result_file.write('" "pyKratos" {} vector OnNodes\n'.format(time))
            self.result_file.write("values\n")
            for node in nodes:
                self.result_file.write("{} {} {}\n".format(self.gid_id(node.Id), node.GetSolutionStepValue(variable[1],0), node.GetSolutionStepValue(variable[2],0)))
        else:
            self.result_file.write("Result \"")
            self.result_file.write(variable)
            self.result_file.write('" "pyKratos" {} scalar OnNodes\n'.format(time))
            self.result_file.write("values\n")
            for node in nodes:
                self.result_file.write("{} {}\n".format(self.gid_id(node.Id), node.GetSolutionStepValue(variable,0)))
        self.result_file.write("end values\n")
        self.result_file.flush()


              

                   
                   
