import React, { useState } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ScrollView, KeyboardAvoidingView, Platform, Alert } from 'react-native';
import { Picker } from '@react-native-picker/picker';

export default function DoctorInfoScreen({ navigation }: { navigation: any }) {
  const [formData, setFormData] = useState({
    fullName: '',
    citizenId: '',
    medicalLicenseNumber: '',
    dateOfBirth: '',
    gender: 'Male',
  });

  const genderOptions = ['Male', 'Female', 'Other'];

  const handleRegister = () => {
    // Validate required fields
    if (!formData.fullName || !formData.citizenId || !formData.medicalLicenseNumber || !formData.dateOfBirth || !formData.gender) {
      Alert.alert('Error', 'Please fill in all required fields');
      return;
    }

    // Calculate age from date of birth
    const age = calculateAge(formData.dateOfBirth);

    // Prepare user data
    const userData = {
      username: formData.fullName,
      citizenId: formData.citizenId,
      medicalLicenseNumber: formData.medicalLicenseNumber,
      dateOfBirth: formData.dateOfBirth,
      gender: formData.gender,
      age: age.toString(),
      email: '', // Can be added later in account settings
      role: 'DOCTOR'
    };

    // Navigate to Home screen with user data
    navigation.reset({
      index: 0,
      routes: [{ 
        name: 'Home',
        params: userData
      }],
    });
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
            <Text style={styles.label}>Full name <Text style={styles.required}>*</Text></Text>
            <TextInput
              style={styles.input}
              placeholder="Xxx Zzz"
              value={formData.fullName}
              onChangeText={(text) => setFormData({...formData, fullName: text})}
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
                setFormData({...formData, citizenId: numericValue});
              }}
              keyboardType="numeric"
              maxLength={12}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Medical license number <Text style={styles.required}>*</Text></Text>
            <TextInput
              style={styles.input}
              placeholder="000-000-0000"
              value={formData.medicalLicenseNumber}
              onChangeText={(text) => setFormData({...formData, medicalLicenseNumber: text})}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Date of Birth <Text style={styles.required}>*</Text></Text>
            <TextInput
              style={styles.input}
              placeholder="DD/MM/YYYY"
              value={formData.dateOfBirth}
              onChangeText={(text) => setFormData({...formData, dateOfBirth: text})}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Gender <Text style={styles.required}>*</Text></Text>
            <View style={styles.pickerContainer}>
              <Picker
                style={styles.picker}
                selectedValue={formData.gender}
                onValueChange={(value) => setFormData({...formData, gender: value})}
              >
                {genderOptions.map((gender) => (
                  <Picker.Item key={gender} label={gender} value={gender} />
                ))}
              </Picker>
            </View>
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
});