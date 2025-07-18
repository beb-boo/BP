import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ScrollView, KeyboardAvoidingView, Platform, Alert, Modal } from 'react-native';
import { Picker } from '@react-native-picker/picker';
import axios from 'axios';
import { API_BASE_URL } from '../../config';
import { authApi, UserCreate } from '../../api/auth';

export default function PatientInfoScreen({ navigation, route }: { navigation: any, route: any }) {
  const [formData, setFormData] = useState({
    fullName: '',
    phoneNumber: '',
    citizenId: '',
    dateOfBirth: '',
    bloodType: 'A+',
    gender: 'male',
    height: '',
    weight: '',
    email: route.params.email,
    password: route.params.password,
    confirmPassword: route.params.confirmPassword,
  });
  const [Loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [otp, setOtp] = useState<string[]>(new Array(6).fill(''));
  const [timer, setTimer] = useState(60);
  
  const otpInputs = useRef<(TextInput | null)[]>([]);

  const bloodTypes = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
  const genderOptions = ['male', 'female', 'other'];

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (modalVisible && timer > 0) {
      interval = setInterval(() => {
        setTimer((prevTimer) => prevTimer - 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [modalVisible, timer]);

  const startTimer = () => {
    setTimer(60);
  };

  const handleResend = async () => {
    setOtp(new Array(6).fill(''));
    const OTP_request = {
      email: formData.email,
      phone_number: formData.phoneNumber,
      purpose: "register",
    };
    try {
      await authApi.requestOTP(OTP_request);
      startTimer();
      Alert.alert('Success', 'A new OTP has been sent.');
    } catch (error) {
      Alert.alert('Error', 'Failed to resend OTP.');
    }
  };

  const handleConfirmOTP = async () => {
    const enteredOtp = otp.join('');
    console.log('OTP confirmed:', enteredOtp);
    const OTP_verify = {
      email: formData.email,
      phone_number: formData.phoneNumber,
      otp_code: enteredOtp,
      purpose: "registration",
    }
    const userData = {
      email: formData.email,
      phone_number: formData.phoneNumber,
      password: formData.password,
      full_name: formData.fullName,
      role: "patient",
      citizen_id: formData.citizenId,
      date_of_birth: formatDateForBackend(formData.dateOfBirth),
      gender: formData.gender,
      blood_type: formData.bloodType,
      height: Number(formData.height),
      weight: Number(formData.weight),
      medical_license: null
    };
    try {
      const response = await authApi.verifyOTP(OTP_verify);
      console.log(response)
      if(response.length != 0){
        Register();
      }
    } catch (error){
      Alert.alert('Error', 'Failed to verify OTP.');
    }
    
    //setModalVisible(false);
    // On successful registration:
    // navigation.navigate('Home'); 
  };

  const Register = async () => {
    setLoading(true); // Start loading indicator

    try {
      // Construct the user data object based on the UserCreate interface
      const userData: UserCreate = {
        email: formData.email, // Use undefined if empty to avoid sending empty string
        phone_number: formData.phoneNumber, // Use undefined if empty
        password: formData.password,
        full_name: formData.fullName,
        role: 'patient',
        citizen_id: formData.citizenId,
        date_of_birth: formatDateForBackend(formData.dateOfBirth), 
        gender: formData.gender,
        blood_type: formData.bloodType,
        height: Number(formData.height),
        weight: Number(formData.weight),
        medical_license: null,
        
      };

      // Call the register function from authApi
      const response = await authApi.register(userData);

      // Handle successful registration
      Alert.alert('Success', response.message || 'Registration successful! Please check your email/phone for OTP.');
      // You might want to navigate the user to an OTP verification screen here
    } catch (error: any) {
      // Handle registration errors
      const errorMessage = error.response?.data?.message || 'Registration failed. Please try again.';
      Alert.alert('Registration Error', errorMessage);
      console.error('Registration error:', error.response?.data || error.message);
    } finally {
      setLoading(false); // Stop loading indicator
    }
  }

  const handleOtpChange = (text: string, index: number) => {
    const newOtp = [...otp];
    newOtp[index] = text;
    setOtp(newOtp);

    if (text.length === 1 && index < 5) {
      otpInputs.current[index + 1]?.focus();
    }
  };

  const handleBackspace = (event: any, index: number) => {
    if (event.nativeEvent.key === 'Backspace' && !otp[index] && index > 0) {
      otpInputs.current[index - 1]?.focus();
    }
  };

  const handleRegister = async () => {
    // Validate required fields
    if (!formData.fullName || !formData.citizenId || !formData.dateOfBirth || !formData.bloodType || !formData.gender) {
      Alert.alert('Error', 'Please fill in all required fields');
      return;
    }

    if (formData.password.length < 8) {
      Alert.alert('Error', 'Password must be more than 8 characters.');
      return;
    }
    
    if (formData.password !== formData.confirmPassword) {
      Alert.alert('Error', 'Passwords do not match.');
      return;
    }
    
    const userData = {
      email: formData.email,
      phone_number: formData.phoneNumber,
      password: formData.password,
      full_name: formData.fullName,
      role: "patient",
      citizen_id: formData.citizenId,
      date_of_birth: formatDateForBackend(formData.dateOfBirth),
      gender: formData.gender,
      blood_type: formData.bloodType,
      height: formData.height ? parseInt(formData.height, 10) : null,
      weight: formData.weight ? parseInt(formData.weight, 10) : null,
      medical_license: null
    };

    console.log("PatientInfoScreen, userData:", userData);

    const OTP_request = {
      email: formData.email,
      phone_number: formData.phoneNumber,
      purpose: "registration",
    }
    console.log(OTP_request);
    
    try {
      await authApi.requestOTP(OTP_request);
      setModalVisible(true);
      startTimer();
    } catch (error) {
      Alert.alert('Error', 'OTP request failed');
    }

  };

  const calculateAge = (birthDate: string) => {
    // Assuming birthDate is in DD/MM/YYYY format
    const [day, month, year] = birthDate.split('/').map(Number);
    const today = new Date();
    const birth = new Date(year, month - 1, day);
    let age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();

    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
      age--;
    }

    return age;
  };

  const formatDateForBackend = (dateStr: string) => {
    // Expecting DD/MM/YYYY
    const [day, month, year] = dateStr.split('/');
    if (!day || !month || !year) return '';
    return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}T00:00:00Z`;
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={{ flex: 1 }}
    >
      <ScrollView
        style={styles.container}
        contentContainerStyle={{ flexGrow: 1 }}
        keyboardShouldPersistTaps="handled"
      >
        <TouchableOpacity
          style={styles.backButton}
          onPress={() => navigation.goBack()}
        >
          <Text>←</Text>
        </TouchableOpacity>

        <Text style={styles.title}>Personal Info</Text>

        <View style={styles.form}>
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Email <Text style={styles.required}>*</Text></Text>
            <TextInput
              style={styles.input}
              placeholder={formData.email}
              value={formData.email}
              onChangeText={(text) => setFormData({ ...formData, email: text })}
              keyboardType="email-address"
              autoCapitalize="none"
            />
          </View>
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Password <Text style={styles.required}>*</Text></Text>
            <TextInput
              style={styles.input}
              placeholder={formData.password}
              value={formData.password}
              onChangeText={(text) => setFormData({ ...formData, password: text })}
              secureTextEntry
            />
          </View>
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Confirm Password <Text style={styles.required}>*</Text></Text>
            <TextInput
              style={styles.input}
              placeholder={formData.confirmPassword}
              value={formData.confirmPassword}
              onChangeText={(text) => setFormData({ ...formData, confirmPassword: text })}
              secureTextEntry
            />
          </View>
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Phone Number <Text style={styles.required}>*</Text></Text>
            <TextInput
              style={styles.input}
              placeholder={formData.phoneNumber}
              value={formData.phoneNumber}
              onChangeText={(text) => setFormData({ ...formData, phoneNumber: text })}
            />
          </View>
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Full name <Text style={styles.required}>*</Text></Text>
            <TextInput
              style={styles.input}
              placeholder="Xxx Zzz"
              value={formData.fullName}
              onChangeText={(text) => setFormData({ ...formData, fullName: text })}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Citizen ID <Text style={styles.required}>*</Text></Text>
            <TextInput
              style={styles.input}
              placeholder="000000000000"
              value={formData.citizenId}
              onChangeText={(text) => {
                const numericValue = text.replace(/[^0-9]/g, '');
                setFormData({ ...formData, citizenId: numericValue });
              }}
              keyboardType="numeric"
              maxLength={12}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Date of Birth <Text style={styles.required}>*</Text></Text>
            <TextInput
              style={styles.input}
              placeholder="DD/MM/YYYY"
              value={formData.dateOfBirth}
              onChangeText={(text) => setFormData({ ...formData, dateOfBirth: text })}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Blood type <Text style={styles.required}>*</Text></Text>
            <View style={styles.pickerContainer}>
              <Picker
                style={styles.picker}
                selectedValue={formData.bloodType}
                onValueChange={(value) => setFormData({ ...formData, bloodType: value })}
              >
                {bloodTypes.map((type) => (
                  <Picker.Item key={type} label={type} value={type} />
                ))}
              </Picker>
            </View>
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Gender <Text style={styles.required}>*</Text></Text>
            <View style={styles.pickerContainer}>
              <Picker
                style={styles.picker}
                selectedValue={formData.gender}
                onValueChange={(value) => setFormData({ ...formData, gender: value })}
              >
                {genderOptions.map((gender) => (
                  <Picker.Item key={gender} label={gender} value={gender} />
                ))}
              </Picker>
            </View>
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Height</Text>
            <TextInput
              style={styles.input}
              placeholder="000 cm"
              value={formData.height}
              onChangeText={(text) => {
                const numericValue = text.replace(/[^0-9]/g, '');
                setFormData({ ...formData, height: numericValue });
              }}
              keyboardType="numeric"
              maxLength={3}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Weight</Text>
            <TextInput
              style={styles.input}
              placeholder="000 kg"
              value={formData.weight}
              onChangeText={(text) => {
                const numericValue = text.replace(/[^0-9]/g, '');
                setFormData({ ...formData, weight: numericValue });
              }}
              keyboardType="numeric"
              maxLength={3}
            />
          </View>

          <TouchableOpacity style={styles.registerButton} onPress={handleRegister}>
            <Text style={styles.registerButtonText}>Register</Text>
          </TouchableOpacity>

          <Text style={styles.terms}>
            By creating an account you agree to Blood Pleasure
          </Text>
          <View style={styles.links}>
            <TouchableOpacity>
              <Text style={styles.link}>Term of Services</Text>
            </TouchableOpacity>
            <TouchableOpacity>
              <Text style={styles.link}>Privacy Policy</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.loginContainer}>
            <Text style={styles.loginText}>Have an account? </Text>
            <TouchableOpacity onPress={() => navigation.navigate('Login')}>
              <Text style={styles.loginLink}>Login</Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>

      <Modal
        animationType="slide"
        transparent={true}
        visible={modalVisible}
        onRequestClose={() => {
          setModalVisible(!modalVisible);
        }}>
        <View style={styles.centeredView}>
          <View style={styles.modalView}>
            <Text style={styles.modalText}>Enter OTP</Text>
            <View style={styles.otpContainer}>
              {otp.map((digit, index) => (
                <TextInput
                  key={index}
                  style={styles.otpInput}
                  keyboardType="numeric"
                  maxLength={1}
                  onChangeText={(text) => handleOtpChange(text, index)}
                  onKeyPress={(e) => handleBackspace(e, index)}
                  value={digit}
                  ref={(ref) => {
                    otpInputs.current[index] = ref;
                  }}
                />
              ))}
            </View>
            <TouchableOpacity
              style={[styles.button, styles.buttonClose]}
              onPress={handleConfirmOTP}>
              <Text style={styles.textStyle}>Confirm</Text>
            </TouchableOpacity>
            <View style={styles.resendContainer}>
              <Text style={styles.resendText}>Didn't receive code? </Text>
              <TouchableOpacity onPress={handleResend} disabled={timer > 0}>
                <Text style={[styles.resendLink, { color: timer > 0 ? '#aaa' : '#4169E1' }]}>
                  {timer > 0 ? `Resend in ${timer}s` : 'Resend'}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    padding: 20,
  },
  backButton: {
    marginTop: 20,
    marginBottom: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 30,
  },
  form: {
    flex: 1,
  },
  inputGroup: {
    marginBottom: 20,
  },
  label: {
    fontSize: 16,
    marginBottom: 8,
  },
  required: {
    color: 'red',
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
  },
  registerButton: {
    backgroundColor: '#4169E1',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 20,
    marginBottom: 20,
  },
  registerButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  terms: {
    textAlign: 'center',
    color: '#666',
    marginBottom: 10,
  },
  links: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 20,
    marginBottom: 20,
  },
  link: {
    color: '#4169E1',
  },
  loginContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 10,
  },
  loginText: {
    color: '#666',
  },
  loginLink: {
    color: '#4169E1',
    fontWeight: '600',
  },
  pickerContainer: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    backgroundColor: '#fff',
  },
  picker: {
    height: 50,
  },
  centeredView: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 22,
  },
  modalView: {
    margin: 20,
    backgroundColor: 'white',
    borderRadius: 20,
    padding: 35,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 5,
  },
  button: {
    borderRadius: 20,
    padding: 10,
    elevation: 2,
    marginTop: 15,
  },
  buttonClose: {
    backgroundColor: '#4169E1',
    paddingHorizontal: 30,
  },
  textStyle: {
    color: 'white',
    fontWeight: 'bold',
    textAlign: 'center',
  },
  modalText: {
    marginBottom: 15,
    textAlign: 'center',
    fontSize: 18,
    fontWeight: 'bold',
  },
  otpContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '80%',
    marginBottom: 20,
  },
  otpInput: {
    width: 40,
    height: 40,
    borderWidth: 1,
    borderColor: '#ddd',
    textAlign: 'center',
    borderRadius: 8,
    fontSize: 18,
  },
  resendContainer: {
    flexDirection: 'row',
    marginTop: 20,
  },
  resendText: {
    color: '#666',
  },
  resendLink: {
    fontWeight: '600',
  },
});