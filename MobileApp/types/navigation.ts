import { NativeStackNavigationProp } from '@react-navigation/native-stack';

export type RootStackParamList = {
  RoleSelect: undefined;
  PatientInfo: undefined;
  DoctorInfo: undefined;
  Login: undefined;
};

export type RootStackNavigationProp = NativeStackNavigationProp<RootStackParamList>; 