# vim: expandtab tabstop=4 shiftwidth=4

# https://www.cloudynights.com/topic/13186-focal-length-in-binoculars/

aperture = 42.0
magnification = 8.0
exit_pupil = aperture / magnification
print('exit pupil = {}'.format(exit_pupil))

# magnification = focal length of objective / focal length of eyepiece
# light path length = focal length of objective + focal length of eyepiece
#light_path_length = 150.0
light_path_length = 65.0
focal_length_of_eyepiece = light_path_length / (magnification + 1)
focal_length_of_objective = light_path_length - focal_length_of_eyepiece
print('focal length of eyepiece = {}'.format(focal_length_of_eyepiece))
print('focal length of objective = {}'.format(focal_length_of_objective))
print('calculcated magnification = {}'.format(focal_length_of_objective / focal_length_of_eyepiece))
print('f/{}'.format(focal_length_of_objective / aperture))
