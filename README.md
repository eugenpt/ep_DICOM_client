* ep_DICOM_client *

provides basic DICOM C_FIND/C_STORE wrappers around pynetdicom functions

for example use change EDC init parameters in ep_DICOM_client.py and run it

Or do smt like this:
~~~~

from ep_DICOM_Client import ep_DICOM_Client

# Init AE_TITLEs and everything
EDC = ep_DICOM_Client(rpath = 'D:\\', 
                      ae_title='EDC', 
                      port=104, 
                      pacs_ip='192.168.2.100',
                      pacs_ae_title='PACS', 
                      pacs_port=104)


# Search for studies of certain Patient:

PatientID = "SAMPLE_ID"

Studies = EDC.getStudyInstanceIdentiers(PatientID)

print('For %s found studies on the following dates:' % PatientID)
for Sj in range(len(Studies)):
    print('%i\t%s\tdate:%s' % (Sj+1,Studies[Sj].PatientID,Studies[Sj].StudyDate))

                  
~~~~                      