import React, { useState, useEffect } from 'react';
import { StyleSheet, View, Alert, Button, TextInput, Image, TouchableOpacity, Modal, ActivityIndicator, Text, ScrollView, KeyboardAvoidingView, Platform, Keyboard, TouchableWithoutFeedback } from 'react-native';
import * as ImagePicker from 'expo-image-picker'
import * as MediaLibrary from 'expo-media-library';
import { Ionicons, MaterialIcons } from '@expo/vector-icons';
import { authApi } from '../api/auth';
import AsyncStorage from '@react-native-async-storage/async-storage';

export default function Account({ navigation, route }: { navigation: any, route: any }) {
  const [loading, setLoading] = useState(true);
  const [username, setUsername] = useState('');
  const [website, setWebsite] = useState('');
  const [avatarUrl, setAvatarUrl] = useState<string | null>(route.params?.avatarUrl || null);
  const [avatarPath, setAvatarPath] = useState("");
  const [mediaPermission, requestMediaPermission] = MediaLibrary.usePermissions();
  const [uploading, setUploading] = useState<boolean>(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editedData, setEditedData] = useState({
    id: null,
    email: '',
    phone_number: '',
    full_name: '',
    role: '',
    citizen_id: '',
    medical_license: '',
    date_of_birth: '',
    gender: '',
    blood_type: '',
    height: '',
    weight: '',
    is_active: false,
    is_email_verified: false,
    is_phone_verified: false,
    last_login: '',
    created_at: '',
    updated_at: '',
  });

  // Separate date fields for editing
  const [dateDay, setDateDay] = useState('');
  const [dateMonth, setDateMonth] = useState('');
  const [dateYear, setDateYear] = useState('');

  // Selection options
  const bloodTypeOptions = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
  const genderOptions = ['male', 'female', 'other'];
  const [userData, setUserData] = useState({
    id: null,
    email: '',
    phone_number: '',
    full_name: '',
    role: '',
    citizen_id: '',
    medical_license: '',
    date_of_birth: '',
    gender: '',
    blood_type: '',
    height: '',
    weight: '',
    is_active: false,
    is_email_verified: false,
    is_phone_verified: false,
    last_login: '',
    created_at: '',
    updated_at: '',
  });

  useEffect(() => {
    (async () => {
      if (!mediaPermission) {
        const { status } = await MediaLibrary.requestPermissionsAsync();
        if (status !== 'granted') {
          alert('Sorry, we need media library permissions to make this work!');
        }
      }
    })();
  }, []);

  useEffect(() => {
    // Always fetch from backend on mount
    const fetchProfile = async () => {
      const response = await authApi.getCurrentUser();
      const profile = response.data.profile; // Extract the profile from nested structure
      setUserData(profile);
    };
    fetchProfile();
  }, []);

  async function updateProfile(userData: any) {
    const {
      full_name,
      phone_number,
      citizen_id,
      date_of_birth,
      gender,
      blood_type,
      height,
      weight,
      medical_license
    } = userData;

    await authApi.updateProfile({
      full_name,
      phone_number,
      citizen_id,
      date_of_birth,
      gender,
      blood_type,
      height,
      weight,
      medical_license
    });
  }

  async function updateAvatar() {
  }

  const handleAvatarChange = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        quality: 1,
      });

      if (!result.canceled && result.assets.length > 0) {
        setAvatarUrl(result.assets[0].uri);
        setShowUploadModal(true); // Show the upload modal after selecting an image
      }
    } catch (error) {
      console.error("Error picking image:", error);
    }
  };

  async function signOut() {
    const response = await authApi.logout();
    console.log('LogOut ' + response)
    await AsyncStorage.removeItem('token')
    navigation.reset({
      index: 0,
      routes: [{ name: 'Login' }],
    });
  }

  const handleEditToggle = () => {
    if (isEditMode) {
      // Save changes
      setUserData(editedData);
      updateProfile(editedData);
      console.log(editedData)
    } else {
      // When entering edit mode, update editedData with current userData
      setEditedData(userData);

      // Parse date of birth for separate fields
      if (userData.date_of_birth) {
        const date = new Date(userData.date_of_birth);
        setDateDay(date.getDate().toString().padStart(2, '0'));
        setDateMonth((date.getMonth() + 1).toString().padStart(2, '0'));
        setDateYear(date.getFullYear().toString());
      }
    }
    setIsEditMode(!isEditMode);
  };

  const handleInputChange = (field: string, value: string) => {
    setEditedData((prev: any) => ({
      ...prev,
      [field]: value
    }));
  };

  const handleDateChange = (type: 'day' | 'month' | 'year', value: string) => {
    if (type === 'day') setDateDay(value);
    if (type === 'month') setDateMonth(value);
    if (type === 'year') setDateYear(value);

    // Update the combined date in editedData
    const day = type === 'day' ? value : dateDay;
    const month = type === 'month' ? value : dateMonth;
    const year = type === 'year' ? value : dateYear;

    if (day && month && year) {
      const formattedDate = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}T00:00:00`;
      setEditedData((prev: any) => ({
        ...prev,
        date_of_birth: formattedDate
      }));
    }
  };

  const formatDateForDisplay = (dateString: string) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB'); // DD/MM/YYYY format
  };

  const DetailField = ({ label, value, field }: { label: string, value: string, field: string }) => (
    <>
      <Text style={styles.detailLabel}>{label}</Text>
      {isEditMode ? (
        <TextInput
          style={[styles.detailValue, styles.editableInput]}
          value={String(editedData[field as keyof typeof editedData] || '')}
          onChangeText={(text) => handleInputChange(field, text)}
          placeholder={`Enter ${label.toLowerCase()}`}
        />
      ) : (
        <Text style={styles.detailValue}>{value}</Text>
      )}
    </>
  );

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      style={{ flex: 1 }}
    >
      <View style={{ flex: 1 }}>
        <ScrollView
          contentContainerStyle={styles.container}
          keyboardShouldPersistTaps="handled"
        >
          <View>
            <Text style={styles.title}>Account</Text>
          </View>

          {/* Blue Card */}
          <View style={styles.blueCard}>
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <View style={styles.avatarCircle}>
                <Ionicons name="person" size={40} color="#4662e6" />
              </View>
              <View style={{ marginLeft: 12 }}>
                {isEditMode ? (
                  <TextInput
                    style={[styles.username, styles.editableInput, { color: '#000', borderColor: '#fff' }]}
                    value={editedData.full_name}
                    onChangeText={(text) => handleInputChange('full_name', text)}
                    placeholder="Enter name"
                    placeholderTextColor="#ffffff80"
                  />

                ) : (
                  <Text style={styles.username}>{userData.full_name}</Text>
                )}
                <View style={styles.patientBadge}>
                  <Text style={styles.patientBadgeText}>{userData.role.toUpperCase()}</Text>
                </View>
              </View>
            </View>
            <View style={styles.citizenCard}>
              <Text style={styles.citizenLabel}>Citizen ID</Text>
              {isEditMode ? (
                <TextInput
                  style={[styles.citizenValue, styles.editableInput]}
                  value={editedData.citizen_id}
                  onChangeText={(text) => handleInputChange('citizen_id', text)}
                  placeholder="Enter citizen ID"
                />
              ) : (
                <Text style={styles.citizenValue}>{userData.citizen_id}</Text>
              )}
              <Text style={styles.detailLabel}>Email</Text>
              <Text style={styles.citizenValue}>{userData.email}</Text>
              <Text style={styles.detailLabel}>Phone</Text>
              {isEditMode ? (
                <TextInput
                  style={[styles.citizenValue, styles.editableInput]}
                  value={editedData.phone_number}
                  onChangeText={(text) => handleInputChange('phone_number', text)}
                  placeholder="Enter Phone"
                  placeholderTextColor="#ffffff80"
                />

              ) : (
                <Text style={styles.citizenValue}>{userData.phone_number}</Text>
              )}
            </View>
          </View>

          {/* Details Card */}
          <View style={styles.detailsCard}>
            <TouchableOpacity style={styles.editProfileBtn} onPress={handleEditToggle}>
              <Text style={[styles.editProfileText, isEditMode && { color: '#1ccfc0' }]}>
                {isEditMode ? 'Save Profile' : 'Edit Profile'}
              </Text>
              <MaterialIcons
                name={isEditMode ? "check" : "edit"}
                size={18}
                color={isEditMode ? "#1ccfc0" : "#e74c3c"}
                style={{ marginLeft: 2 }}
              />
            </TouchableOpacity>
            <View style={styles.detailsRow}>
              <View style={styles.detailsColLeft}>
                {isEditMode ? (
                  <>
                    <Text style={styles.detailLabel}>Date of Birth</Text>
                    <View style={styles.dateInputContainer}>
                      <TextInput
                        style={[styles.dateInput, styles.editableInput]}
                        value={dateDay}
                        onChangeText={(text) => handleDateChange('day', text)}
                        placeholder="DD"
                        keyboardType="numeric"
                        maxLength={2}
                      />
                      <Text style={styles.dateSeparator}>/</Text>
                      <TextInput
                        style={[styles.dateInput, styles.editableInput]}
                        value={dateMonth}
                        onChangeText={(text) => handleDateChange('month', text)}
                        placeholder="MM"
                        keyboardType="numeric"
                        maxLength={2}
                      />
                      <Text style={styles.dateSeparator}>/</Text>
                      <TextInput
                        style={[styles.dateInput, styles.editableInput]}
                        value={dateYear}
                        onChangeText={(text) => handleDateChange('year', text)}
                        placeholder="YYYY"
                        keyboardType="numeric"
                        maxLength={4}
                      />
                    </View>
                    <Text style={styles.detailLabel}>Blood Type</Text>
                    <View style={styles.pickerContainer}>
                      {bloodTypeOptions.map((option) => (
                        <TouchableOpacity
                          key={option}
                          style={[
                            styles.optionButton,
                            editedData.blood_type === option && styles.selectedOption
                          ]}
                          onPress={() => handleInputChange('blood_type', option)}
                        >
                          <Text style={[
                            styles.optionText,
                            editedData.blood_type === option && styles.selectedOptionText
                          ]}>
                            {option}
                          </Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                    <Text style={styles.detailLabel}>Height</Text>
                    <TextInput
                      style={[styles.citizenValue, styles.editableInput]}
                      value={editedData.height}
                      onChangeText={(text) => handleInputChange('height', text)}
                      placeholder="Enter height"
                    />
                  </>
                ) : (
                  <>
                    <Text style={styles.detailLabel}>Date of Birth</Text>
                    <Text style={styles.citizenValue}>{formatDateForDisplay(userData.date_of_birth)}</Text>
                    <Text style={styles.detailLabel}>Blood Type</Text>
                    <Text style={styles.citizenValue}>{userData.blood_type}</Text>
                    <Text style={styles.detailLabel}>Height</Text>
                    <Text style={styles.citizenValue}>{userData.height}</Text>
                  </>
                )}
              </View>
              <View style={styles.detailsColRight}>
                {isEditMode ? (
                  <>
                    <Text style={styles.detailLabel}></Text>
                    <Text style={styles.detailLabel}></Text>
                    {/* <Text style={styles.detailLabel}>Age</Text>
                    <TextInput
                      style={[styles.citizenValue, styles.editableInput]}
                      value={editedData.age}
                      onChangeText={(text) => handleInputChange('age', text)}
                      placeholder="Enter age"
                    /> */}
                    <Text style={styles.detailLabel}>Gender</Text>
                    <View style={styles.pickerContainer}>
                      {genderOptions.map((option) => (
                        <TouchableOpacity
                          key={option}
                          style={[
                            styles.optionButton,
                            editedData.gender === option && styles.selectedOption
                          ]}
                          onPress={() => handleInputChange('gender', option)}
                        >
                          <Text style={[
                            styles.optionText,
                            editedData.gender === option && styles.selectedOptionText
                          ]}>
                            {option}
                          </Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                    <Text style={styles.detailLabel}>Weight</Text>
                    <TextInput
                      style={[styles.citizenValue, styles.editableInput]}
                      value={editedData.weight}
                      onChangeText={(text) => handleInputChange('weight', text)}
                      placeholder="Enter weight"
                    />
                  </>
                ) : (
                  <>
                    <Text style={styles.detailLabel}>Age</Text>
                    <Text style={styles.citizenValue}></Text>
                    <Text style={styles.detailLabel}>Gender</Text>
                    <Text style={styles.citizenValue}>{userData.gender}</Text>
                    <Text style={styles.detailLabel}>Weight</Text>
                    <Text style={styles.citizenValue}>{userData.weight}</Text>
                  </>
                )}
              </View>
            </View>
          </View>

          {/* Sign Out Button */}
          <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
            <View>
              <TouchableOpacity style={styles.signOutBtn} onPress={signOut}>
                <Text style={styles.signOutText}>Sign Out</Text>
              </TouchableOpacity>
            </View>
          </TouchableWithoutFeedback>

          {/* Add extra padding at the bottom to ensure content is above the bottom bar */}
          <View style={{ height: 100 }} />
        </ScrollView>

        {/* Bottom Bar */}
        {isEditMode ? (
          <View style={{}}>

          </View>
        ) : (
          <View style={styles.bottomBar}>
            <TouchableOpacity style={styles.bottomBarIcon} onPress={() => navigation.navigate("Home")}>
                <Ionicons name="home" size={28} color="#fff" />
              </TouchableOpacity>

            <TouchableOpacity style={styles.bottomBarIcon} onPress={() => navigation.navigate("Camera")}>
              <Ionicons name="scan" size={28} color="#fff" />
            </TouchableOpacity>
            
            <TouchableOpacity style={styles.bottomBarIcon} onPress={() => userData.role === 'doctor' ? (navigation.navigate("Patientlist")) : (navigation.navigate("Doctorlist"))}>
              <Ionicons name="medkit" size={28} color="#fff" />
            </TouchableOpacity>

            <TouchableOpacity style={styles.bottomBarIconActive}>
              <Ionicons name="person-circle-outline" size={28} color="#1ccfc0" />
            </TouchableOpacity>
          </View>
        )}
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    backgroundColor: '#fff',
    paddingTop: 32,
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#111',
    alignSelf: 'flex-start',
    marginLeft: 24,
    marginBottom: 16,
    marginTop: 32,
  },
  blueCard: {
    backgroundColor: '#4662e6',
    borderRadius: 20,
    padding: 20,
    marginBottom: 24,
    width: '90%',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 6,
  },
  avatarCircle: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#fff',
    justifyContent: 'center',
    alignItems: 'center',
  },
  username: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 18,
    marginBottom: 10,
  },
  patientBadge: {
    backgroundColor: '#ffe066',
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 2,
    alignSelf: 'flex-start',
  },
  patientBadgeText: {
    color: '#222',
    fontWeight: 'bold',
    fontSize: 13,
  },
  citizenCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 14,
    marginTop: 18,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.10,
    shadowRadius: 4,
    elevation: 2,
  },
  citizenLabel: {
    fontWeight: 'bold',
    fontSize: 16,
    color: '#222',
    marginBottom: 2,
  },
  citizenValue: {
    fontSize: 15,
    color: '#222',
  },
  detailsCard: {
    backgroundColor: '#fff',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#222',
    width: '90%',
    marginBottom: 32,
    padding: 20,
    position: 'relative',
  },
  editProfileBtn: {
    position: 'absolute',
    right: 16,
    top: 16,
    flexDirection: 'row',
    alignItems: 'center',
  },
  editProfileText: {
    color: '#e74c3c',
    fontSize: 15,
    fontWeight: '500',
    marginRight: 2,
  },
  detailsRow: {
    flexDirection: 'row',
    marginTop: 8,
  },
  detailsColLeft: {
    flex: 1,
    alignItems: 'flex-start',
  },
  detailsColRight: {
    flex: 1,
    alignItems: 'flex-start',
  },
  detailLabel: {
    fontWeight: 'bold',
    fontSize: 15,
    color: '#222',
    marginTop: 10,
  },
  detailValue: {
    fontSize: 15,
    color: '#222',
    marginBottom: 2,
  },
  signOutBtn: {
    backgroundColor: '#e74c3c',
    borderRadius: 20,
    paddingVertical: 14,
    paddingHorizontal: 48,
    alignItems: 'center',
    marginTop: 16,
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.10,
    shadowRadius: 4,
    elevation: 2,
  },
  signOutText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 17,
  },
  bottomBar: {
    position: 'absolute',
    bottom: 16,
    left: 10,
    right: 10,
    height: 64,
    backgroundColor: '#222',
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    borderRadius: 32,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 8,
  },
  bottomBarIcon: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  bottomBarIconActive: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'transparent',
  },
  editableInput: {
    borderWidth: 1,
    borderColor: '#808080',
    borderRadius: 10,
    backgroundColor: '#f2f2f2',
    padding: 5,
    minWidth: 80,
    marginVertical: 2,
  },
  dateInputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 2,
  },
  dateInput: {
    borderWidth: 1,
    borderColor: '#808080',
    borderRadius: 10,
    backgroundColor: '#f2f2f2',
    padding: 5,
    width: 60,
    textAlign: 'center',
  },
  dateSeparator: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#222',
    marginHorizontal: 8,
  },
  pickerContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginVertical: 2,
  },
  optionButton: {
    borderWidth: 1,
    borderColor: '#808080',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginRight: 8,
    marginBottom: 8,
    backgroundColor: '#f2f2f2',
  },
  selectedOption: {
    backgroundColor: '#4662e6',
    borderColor: '#4662e6',
  },
  optionText: {
    fontSize: 14,
    color: '#222',
  },
  selectedOptionText: {
    color: '#fff',
    fontWeight: 'bold',
  },
});


