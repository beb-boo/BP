import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image } from 'react-native';

export default function RoleSelectScreen({ navigation }: { navigation: any }) {

  const handleRoleSelect = (role: 'patient' | 'doctor') => {
    navigation.navigate(role === 'patient' ? 'PatientInfo' : 'DoctorInfo');
  };

  return (
    <View style={styles.container}>
      <TouchableOpacity 
        style={styles.backButton}
        onPress={() => navigation.goBack()}
      >
        <Text>←</Text>
      </TouchableOpacity>

      <Text style={styles.title}>What is your Role?</Text>
      <Text style={styles.subtitle}>Your access to content is depend on your role</Text>

      <View style={styles.rolesContainer}>
        <TouchableOpacity 
          style={styles.roleCard}
          onPress={() => handleRoleSelect('patient')}
        >
          <Image 
            source={require('../assets/role-select-norm.png')}
            style={styles.roleImage}
          />
          <Text style={styles.roleText}>Patient</Text>
        </TouchableOpacity>

        <TouchableOpacity 
          style={styles.roleCard}
          onPress={() => handleRoleSelect('doctor')}
        >
          <Image 
            source={require('../assets/role-select-doc.png')}
            style={styles.roleImage}
          />
          <Text style={styles.roleText}>Doctor</Text>
        </TouchableOpacity>
      </View>
    </View>
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
    marginBottom: 10,
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    marginBottom: 40,
  },
  rolesContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    marginTop: 20,
  },
  roleCard: {
    alignItems: 'center',
    padding: 20,
    borderRadius: 20,
    backgroundColor: '#fff',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
    width: '45%',
  },
  roleImage: {
    width: 120,
    height: 120,
    marginBottom: 10,
  },
  roleText: {
    fontSize: 18,
    fontWeight: '600',
    marginTop: 10,
  },
});

