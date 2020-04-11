# -*- coding: utf-8 -*-
"""
Created on Mon Oct 14 17:15:53 2019

@author: ep
"""

import copy
import os
import pynetdicom 
import time

import pydicom
from pydicom.dataset import Dataset

from pynetdicom import AE, evt, StoragePresentationContexts
from pynetdicom.sop_class import PatientRootQueryRetrieveInformationModelFind
from pynetdicom.sop_class import StudyRootQueryRetrieveInformationModelFind


# %%
def combineDatasets(*argv):
    """
    combines pydicom Datasets, adding fields/values from later paramters

    Parameters
    ----------
    *argv : Datasets to combine

    Returns
    -------
    D : combined Dataset.

    """
    D = copy.deepcopy(argv[0])
    for a in argv[1:]:
        for k in a._dict:
            D._dict[k] = a._dict[k]
    return D

class ep_DICOM_Client:
    """
        Simple implementation of DICOM Client for home use
        (wrapper around pynetdicom functions)
    """
    dataset_save_filter_fun = lambda _:True  
    # sample filter fun:
    # dataset_save_filter_fun = lambda D:(('brain'  in str(D.SeriesDescription).lower())or('bone' in str(D.SeriesDescription).lower()))
    
    def __init__(self, rpath='C:\\temp', ae_title='AE_TITLE', port=104, pacs_ip='192.168.2.100', pacs_ae_title='PACS', pacs_port=104):
        """
        
        ae_title, port - settings for client, 
                            port is only important for downloads
        
        pacs_ip, pacs_ae_title, pacs_port
            - settings for PACS (any system to send Queries to)
        
        rpath - root path for DICOMs to be saved to
        
        """
        ae = AE(ae_title)
        
        # Add a requested presentation context
        ae.add_requested_context(PatientRootQueryRetrieveInformationModelFind)
        ae.add_requested_context(StudyRootQueryRetrieveInformationModelFind)
        ae.add_requested_context(pynetdicom.sop_class.StudyRootQueryRetrieveInformationModelMove)
        ae.add_requested_context(pynetdicom.sop_class.PatientRootQueryRetrieveInformationModelMove)
        ae.supported_contexts = StoragePresentationContexts 
        
        self.handlers = [(evt.EVT_C_STORE, self.handle_store)]

        
        self.ae = ae
        self.ae_title = ae_title
        self.port = port
        self.pacs_ip = pacs_ip
        self.pacs_ae_title = pacs_ae_title
        self.pacs_port = pacs_port
        
        self.ae_title = ae_title
    
    
        self.rpath = rpath
        if not os.path.isdir(rpath):
            os.mkdir(rpath)
            
        self.ES = []
        self.DICOMpaths = []


    def getIdentifiers(self, ds, verbose=0):
        """
        `private` function for basic C_FIND query based on ds

        Parameters
        ----------
        ds : Dataset with search parameters

        Returns
        -------
        R : list of identifiers (Datasets) returned from C_FIND

        """
        R = []
        
        assoc = self.ae.associate(self.pacs_ip, self.pacs_port, ae_title=self.pacs_ae_title)
    
        if assoc.is_established:
            # Use the C-FIND service to send the identifier
            responses = assoc.send_c_find(ds, 'P')#PatientRootQueryRetrieveInformationModelFind)
        
            for (status, identifier) in responses:
                if status:
                    if(verbose):
                        print('C-FIND query status: 0x{0:04x}'.format(status.Status))
        
                    # If the status is 'Pending' then identifier is the C-FIND response
                    if status.Status in (0xFF00, 0xFF01):
                        #UIDs.append(identifier.StudyInstanceUID)
                        identifier = combineDatasets(ds, identifier)
                        R.append(identifier)
                        if(verbose):
                            print(identifier)
                        #aaa
                else:
                    if(verbose):
                        print('Connection timed out, was aborted or received invalid response')
        
             # Release the association
            assoc.release()
        else:
            if(verbose):
                print('Association rejected, aborted or never connected')
            
        return R

    def getStudyInstanceIdentiers(self, _ds, verbose=0):
            
        if(type(_ds)==type('')):
            ID = _ds
            ds = Dataset()
            ds.PatientID = ID
        else:
            ds = copy.deepcopy(_ds)
            pass
        
        ds.QueryRetrieveLevel = 'STUDY'
        ds.StudyInstanceUID=""
    
        if not hasattr(ds,'StudyDate'):
            ds.StudyDate=''
        if not hasattr(ds,'StudyID'):
            ds.StudyID=''
        if not hasattr(ds,'Modality'):
            ds.Modality=''
        if not hasattr(ds,'StudyDescription'):
            ds.StudyDescription=''
        
        return self.getIdentifiers(ds, verbose=verbose)


    def getSeriesInstanceIdentiers(self,_ds, verbose=0):
        """
        returns Series Identifiers of Study

        Parameters
        ----------
        _ds : dataset or StudyInstanceUID 
            provides as search parameter for DICOM Query
        verbose : bool, optional
            DESCRIPTION. The default is 0.

        Returns
        -------
        list of DICOM identifiers
            DESCRIPTION.

        """
        if(type(_ds)==type('')):
            ds = Dataset()
            ds.StudyInstanceUID = _ds
            ds.StudyDate=''
            ds.StudyID=''
            ds.Modality=''
            ds.StudyDescription=''
        else:
            ds = copy.deepcopy(_ds)

        ds.QueryRetrieveLevel = 'SERIES'
        
        if not hasattr(ds,'SeriesInstanceUID'):
            ds.SeriesInstanceUID = ""
        if not hasattr(ds,'SeriesDescription'):
            ds.SeriesDescription = ""
        if not hasattr(ds,'SeriesNumber'):
            ds.SeriesNumber = 0
        if not hasattr(ds,'Modality'):
            ds.Modality = ''
            
            
        if not hasattr(ds,'NumberOfSeriesRelatedInstances'):
            ds.NumberOfSeriesRelatedInstances = 0 #number of images, is handy
       
        return self.getIdentifiers(ds, verbose=verbose)
    
    def getImageIdentifiers(self,_ds, verbose=0):
        """
        returns Image (SOP) Identifiers of Series

        Parameters
        ----------
        _ds : dataset or SeriesInstanceUID 
            provides as search parameter for DICOM Query
        verbose : bool, optional
            DESCRIPTION. The default is 0.

        Returns
        -------
        list of DICOM identifiers
            DESCRIPTION.

        """
        
        if(type(_ds)==type('')):
            ds = Dataset()
            ds.SeriesInstanceUID = _ds
        else:
            ds = copy.deepcopy(_ds)

        ds.QueryRetrieveLevel = 'IMAGE'
      
        if not hasattr(ds,'StudyID'):
            ds.StudyInstanceUID=''
        if not hasattr(ds,'SeriesInstanceUID'):
            ds.SeriesInstanceUID = ""
        if not hasattr(ds,'SOPInstanceUID'):
            ds.SOPInstanceUID = ''
        if not hasattr(ds,'InstanceNumber'):
            ds.InstanceNumber=''
    
        return self.getIdentifiers(ds, verbose=verbose)

    
    
    def getDICOM_fpath(self, D, force_unique=0):
        """
        returns supposed filepath for DICOM dataset D

        Parameters
        ----------
        D : Image level Dataset 
            (with SOPInstanceUID, InstanceNumber, etc.)
            
        force_unique : bool, default=False,
                    True => adds random int tofilename
        Returns
        -------
        fpath : path to file

        """
        # Create folder for the patient, if not existent
        if not os.path.isdir(os.path.join(self.rpath,D.PatientID)):
            os.mkdir(os.path.join(self.rpath,D.PatientID))
        
        # prettify series number
        hSeriesNumber = str(D.SeriesNumber)
        try:
            hSeriesNumber='%04i' % int(hSeriesNumber)
        except:
            
            hSeriesNumber='0'*(4-len(hSeriesNumber)) + hSeriesNumber
        
        series_dir = hSeriesNumber+'_'+D.SeriesDescription.replace('*','_')
        if not os.path.isdir(os.path.join(self.rpath,D.PatientID,series_dir)):
            os.mkdir(os.path.join(self.rpath,D.PatientID,series_dir))
        
        
        # prettify slice_number
        slice_num = D.InstanceNumber
        try:
            slice_num = '%03i' % int(slice_num)
        except:
            slice_num = '0'*(3-len(slice_num)) + slice_num
        
        slice_num = D.SOPInstanceUID+'_'+slice_num
    
        if(force_unique):
            # Template in case I missed sth and I need unique name anyway    
            slice_num = slice_num+ ('%05i' % random.randint(0,99999))
    
        fname = D.PatientID+'__'+D.StudyDate+'__'+D.StudyID+'__'+D.Modality+'__'+D.StudyDescription+'__'+hSeriesNumber+'__'+D.SeriesDescription+'_'+slice_num+'.dcm'
        
        fname = fname.replace('*','_')
        
        fpath = os.path.join(self.rpath,D.PatientID,series_dir,fname)
        return fpath
    

    def handle_store(self,event):
        """Handle a C-STORE service request"""
        
        if(0):
            self.ES.append(copy.deepcopy(event))
        
        D = event.dataset
        
        fpath = self.getDICOM_fpath(D)
        print(fpath)
        
        self.DICOMpaths.append(fpath)
    
        
        if(self.dataset_save_filter_fun):
            if( not self.dataset_save_filter_fun(D)):
                # not save
                return 0
    
        #if(not os.path.isfile(fpath)):
        pydicom.dcmwrite(fpath,D)
        
        return 0x0000


    def DownloadUID_any(self,_ds):
        ds = copy.deepcopy(_ds)
        
        if not hasattr(ds,'Modality'):
            ds.Modality = ''
        if not hasattr(ds,'StudyDate'):
            ds.StudyDate = ''
        if not hasattr(ds,'SeriesNumber'):
            ds.SeriesNumber = 0
        if not hasattr(ds,'SeriesDescription'):
            ds.SeriesDescription = ''
        
        self.scp = self.ae.start_server(('', self.port), block=False, evt_handlers=self.handlers, ae_title=self.ae_title)
        
        # Associate with peer AE
        assoc = self.ae.associate(self.pacs_ip, self.pacs_port, ae_title=self.pacs_ae_title)
        if assoc.is_established:
            # Use the C-MOVE service to send the identifier
            responses = assoc.send_c_move( ds, self.ae_title.encode('utf-8'), 'P')#PatientRootQueryRetrieveInformationModelMove)
        
            for (status, identifier) in responses:
                if status:
                    #print('C-MOVE query status: 0x{0:04x}'.format(status.Status))
        
                    # If the status is 'Pending' then `identifier` is the C-MOVE response
                    if status.Status in (0xFF00, 0xFF01):
                        print(identifier)
                else:
                    print('Connection timed out, was aborted or received invalid response')
        
            # Release the association
            assoc.release()
        else:
            print('Association rejected, aborted or never connected')
    
        # Stop our Storage SCP
        self.scp.shutdown()


    def DownloadUID(self,ID,UID,SeriesUID=None):
        ds = Dataset()
        ds.QueryRetrieveLevel = 'SERIES'
        # Unique key for PATIENT level
        ds.PatientID = ID
        #ds.SeriesDescription="*brain*"
        #ds.StudyID = '4456'
        ## Unique key for STUDY level
        ds.StudyInstanceUID = UID#'1.2.3'
        ds.StudyDate = ''
        
        ds.SeriesNumber = 0
        ds.SeriesDescription = "*"
        ## Unique key for SERIES level
        
        if(SeriesUID is None):
            ds.SeriesInstanceUID = '*'
        else:
            ds.SeriesInstanceUID = SeriesUID
    
    
        self.scp = self.ae.start_server(('', self.port), block=False, evt_handlers=self.handlers, ae_title=self.ae_title)

        # Associate with peer AE at IP 127.0.0.1 and port 11112
        assoc = self.ae.associate(self.pacs_ip, self.pacs_port, ae_title=self.pacs_ae_title)
        
        if assoc.is_established:
            # Use the C-MOVE service to send the identifier
            responses = assoc.send_c_move( ds, self.ae_title.encode('utf-8'), 'P')#PatientRootQueryRetrieveInformationModelMove)
        
            for (status, identifier) in responses:
                if status:
                    #print('C-MOVE query status: 0x{0:04x}'.format(status.Status))
        
                    # If the status is 'Pending' then `identifier` is the C-MOVE response
                    if status.Status in (0xFF00, 0xFF01):
                        #print(identifier)
                        pass
                else:
                    print('Connection timed out, was aborted or received invalid response')
        
            # Release the association
            assoc.release()
        else:
            print('Association rejected, aborted or never connected')
    
    
        # Stop our Storage SCP
        self.scp.shutdown()
# %%


if __name__ == '__main__':
    
    # Change these for your setup
    #   also do not forget to setup PACS to recognize client's ae_title/port
    EDC = ep_DICOM_Client(rpath='D:\\DICOM\\', 
                          ae_title='ae_title', 
                          port=5678, 
                          pacs_ip='192.168.2.100',
                          pacs_ae_title='PACS', 
                          pacs_port=104)
    
    # %%
    
    while(1):
        Identifiers = []
        while not Identifiers:
            ID = input('Enter PatientID (empty or "Q" to quit):')
            
            if(ID == ''):
                ID = 'test_head_29032020'
            
            if(ID in {'','q','Q'}):
                break
            Identifiers = EDC.getStudyInstanceIdentiers(ID)
            if(len(Identifiers)==0):
                print('Nothing found.. try again.')
            else:
                break
    
        if(ID in {'','q','Q'}):
            break
    
        # %%
        
        print('Found result on dates:')
        for Ij in range(len(Identifiers)):
            print('%i\t%s\tdate:%s' % (Ij+1,Identifiers[Ij].PatientID,Identifiers[Ij].StudyDate))
        
        while(1):
            r = input('Enter number (1..%i) or "C" to Cancel or "Q" to quit:' % (len(Identifiers)))
            try:
                j=int(r)
                if((j>=1)and(j<=len(Identifiers))):
                    break
            except ValueError:
                if(r.lower() in ['q','c']):
                    break
    
        if(r.lower()=='c'):
            continue
        if(r.lower()=='q'):
            break
        
        # %% List Series
        Identifierj = j-1
        SIdentifiers = EDC.getSeriesInstanceIdentiers(Identifiers[Identifierj])
        
        SN_Ij_d = {int(SIdentifiers[Ij].SeriesNumber) : Ij for Ij in range(len(SIdentifiers))}
        
        for Ij in range(len(SIdentifiers)):
            print('%i\t%s\t%s' % (Ij+1,SIdentifiers[Ij].SeriesNumber,SIdentifiers[Ij].SeriesDescription))
        
        
        
        while(1):
            r = input('Enter number (1..%i) or SeriesNumber (%i..%i) or "C" to Cancel or "Q" to quit:' % (len(SIdentifiers),min(list(SN_Ij_d.keys())),max(list(SN_Ij_d.keys()))))
            try:
                sj=int(r)
                if((sj>=1)and(sj<=len(SIdentifiers))):
                    SIj = sj-1
                    break
                if(sj in SN_Ij_d):
                    SIj = SN_Ij_d[sj]
                    break
            except ValueError:
                if(r.lower() in ['q','c']):
                    break
    
        if(r.lower()=='c'):
            continue
        if(r.lower()=='q'):
            break
        
        # %%
        
        print('Selected Series %s %s' % (SIdentifiers[SIj].SeriesNumber,SIdentifiers[SIj].SeriesDescription))
        
        
        # %%
        
        ImIs = EDC.getImageIdentifiers(SIdentifiers[SIj])
        
        ImIs_combined = [combineDatasets(Identifiers[Identifierj],SIdentifiers[SIj],ImI) for ImI in ImIs]
        
        
        nAlreadyHave = 0
        for ImI in ImIs_combined:
            fpath = EDC.getDICOM_fpath(ImI)
            if os.path.isfile(fpath):
                nAlreadyHave = nAlreadyHave + 1
                #print('+')
            else:
                pass
                #print('-')
        
        print('Already downloaded %i/%i files' % (nAlreadyHave,len(ImIs)))
            
        
        if(0):
            tStart = time.time()
            print('Starting NEW Download')
        
            for ImI in ImIs_combined:
                #print(ImI.InstanceNumber)
                EDC.DownloadUID_any(ImI)
            
            print('Finished in %.3fs' % (time.time()- tStart))
            # 272.2s. huh, about 2 times slower
    
        if(1):
            # OLD download
            tStart = time.time()
            print('Starting OLD Download')
        
            EDC.DownloadUID(ID,SIdentifiers[SIj].StudyInstanceUID,SIdentifiers[SIj].SeriesInstanceUID)
            
            print('Finished in %.3fs' % (time.time()- tStart))
            # 173.3s
        
            


""" """
#
