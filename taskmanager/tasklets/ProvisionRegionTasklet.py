'''
Created on Jan 14, 2014

@author: David Daeschler
'''

from tasklets.TaskletBase import TaskletBase
from inworldz.maestro.environment.RegionEntry import RegionState

class ProvisionRegionTasklet(TaskletBase):
    '''
    Tasklet for provisioning new regions on a host
    '''

        
    def execute(self):
        # ProvisionRegionTasklet
        # {
        #    "createEstate": "true/false",
        #    "estateName": "[name of estate for new estate]",
        #    "estateId": "[uuid of existing estate]",
        #    "simName": "[name for new sim]",
        #    "xloc": "[x grid location]",
        #    "yloc": "[y grid location]",
        #    "simOwner": "[uuid]",
        #    "productType": "[product type id]"
        # }
        host = self.session.api.RegionHost.get_all()[0]
        
        if self.args['simOwner'] == None:
            raise Exception("simOwner not specified")
        if self.args['simOwner'] == '':
            raise Exception("simOwner was blank")

        user = self.session.api.User.FindByUserID(self.args['simOwner'])
        if user == None:
            raise Exception("Sim owner {0} could not be found".format(self.args['simOwner']))
        
        estate = None
        
        #do we need to create a new estate?
        if self.args['createEstate'] == "true":
            estate = self.session.api.Estate.create({ 'estate_name' : self.args['estateName'], 'estate_owner' : user})
        else:
            estate = self.session.api.Estate.FindByEstateID(self.args['estateId'])
            if estate == None:
                raise Exception("Estate {0} given for new region could not be found".format(self.args['estateId']))
            
        estateId = self.session.api.Estate.get_estate_id(estate)
        
        region_record = {
         'sim_name': self.args['simName'],
         'sim_location_x': self.args['xloc'],
         'sim_location_y': self.args['yloc'],
         'estate_id' : estateId,
         'master_avatar_uuid': user,
         'region_product': self.args['productType']
         } 
    
        region = self.session.api.RegionHost.ProvisionRegion(host, region_record)
        
        self.session.api.Region.UpdateToLatest(region)
        self.session.api.Region.Reconfigure(region)
        
        self.session.api.Region.ChangeState(region, RegionState.DeployedStarting)
        self.session.api.Region.Start(region)
