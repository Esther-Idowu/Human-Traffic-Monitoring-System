# -*- coding: utf-8 -*-
"""
Created on Thu Sep 24 11:55:07 2020

@author: User
"""
class TrackableObject:
    def __init__(self, objectID, centroid):
        self.objectID = objectID
        self.centroids = [centroid]

        self.counted = False
    

