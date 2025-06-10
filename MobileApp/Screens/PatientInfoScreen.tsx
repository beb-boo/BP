import React, { useState } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ScrollView } from 'react-native';

export default function PatientInfoScreen({ navigation }: { navigation: any }) {
  const [formData, setFormData] = useState({
    fullName: '',
    citizenId: '',
    dateOfBirth: '',
    bloodType: '',
    gender: '',
    height: '',
    weight: '',
  });

  const handleRegister = () => {
    // Handle registration logic here
    console.log('Patient registration:', formData);
  };

  return (
    <ScrollView style={styles.container}>
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
            onChangeText={(text) => setFormData({...formData, citizenId: text})}
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
          <Text style={styles.label}>Blood type <Text style={styles.required}>*</Text></Text>
          <TextInput
            style={styles.input}
            placeholder="A"
            value={formData.bloodType}
            onChangeText={(text) => setFormData({...formData, bloodType: text})}
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>Gender <Text style={styles.required}>*</Text></Text>
          <TextInput
            style={styles.input}
            placeholder="Female"
            value={formData.gender}
            onChangeText={(text) => setFormData({...formData, gender: text})}
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>Height</Text>
          <TextInput
            style={styles.input}
            placeholder="000 cm"
            value={formData.height}
            onChangeText={(text) => setFormData({...formData, height: text})}
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>Weight</Text>
          <TextInput
            style={styles.input}
            placeholder="000 kg"
            value={formData.weight}
            onChangeText={(text) => setFormData({...formData, weight: text})}
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
});