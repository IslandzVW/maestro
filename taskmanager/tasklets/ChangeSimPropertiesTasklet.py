'''
Created on Jan 24, 2014

@author: David Daeschler
'''

from tasklets.TaskletBase import TaskletBase

class ChangeSimPropertiesTasklet(TaskletBase):
    '''
    Tasklet that changes settable properties on a sim like its name and location
    '''

        
    def execute(self):
        # ChangeSimPropertiesTasklet
        # {
        #    "regionId": "[uuid of region to change]",
        #    [optional] "name": "[new name]",
        #    [optional] "xloc": "[new x location]",
        #    [optional] "yloc": "[new y location]",
        #    [optional] "ownerId": "[uuid of new owner]"
        #    [optional] "estateId": "[uuid of new estate]"
        # }
        
        region = self.args['regionId']
        
        if 'name' in self.args:
            self.session.api.Region.set_sim_name(region, self.args['name'])
        if 'xloc' in self.args and 'yloc' in self.args:
            self.session.api.Region.set_sim_location(region, self.args['xloc'], self.args['yloc'])
        if 'ownerId' in self.args:
            self.session.api.Region.set_master_avatar_uuid(region, self.args['ownerId'])
        if 'estateId' in self.args:
            self.session.api.Region.set_estate_id(region, self.args['estateId'])
            
        self.session.api.Region.Reconfigure(region)
        
        
        
        