import React, { useState, useEffect } from 'react';
import { StyleSheet, View, Alert, Button, TextInput, Image, TouchableOpacity, Modal, ActivityIndicator, Text, ScrollView, KeyboardAvoidingView, Platform, Keyboard, TouchableWithoutFeedback } from 'react-native';
import * as ImagePicker from 'expo-image-picker'
import * as MediaLibrary from 'expo-media-library';
import { Ionicons, MaterialIcons } from '@expo/vector-icons';

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
    username: '',
    citizenId: '',
    dateOfBirth: '',
    bloodType: '',
    height: '',
    weight: '',
    age: '',
    gender: '',
    email: '',
    role: '',
  });
  const [userData, setUserData] = useState({
    username: '',
    citizenId: '',
    dateOfBirth: '',
    bloodType: '',
    height: '',
    weight: '',
    age: '',
    gender: '',
    email: '',
    role: '',
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
    if (route.params?.userData) {
        setUserData(route.params.userData);
        setEditedData(route.params.userData);
    }
}, [route.params?.userData]);

  async function getProfile() {

  }

  async function updateProfile() {

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

  const uploadImage = async () => {

  };

  async function signOut() {
    navigation.reset({
      index: 0,
      routes: [{ name: 'Login' }],
    });
  }

  async function handleUpdate() {

  }

  const cancelUpload = () => {
    setAvatarUrl(null); // Clear the photo URI
    setShowUploadModal(false); // Close the modal
  };

  const handleEditToggle = () => {
    if (isEditMode) {
      // Save changes
      setUserData(editedData);
    }
    setIsEditMode(!isEditMode);
  };

  const handleInputChange = (field: string, value: string) => {
    setEditedData((prev: any) => ({
      ...prev,
      [field]: value
    }));
  };

  const DetailField = ({ label, value, field }: { label: string, value: string, field: string }) => (
    <>
      <Text style={styles.detailLabel}>{label}</Text>
      {isEditMode ? (
        <TextInput
          style={[styles.detailValue, styles.editableInput]}
          value={editedData[field as keyof typeof editedData]}
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
                    style={[styles.username, styles.editableInput, { color: '#fff', borderColor: '#fff' }]}
                    value={editedData.username}
                    onChangeText={(text) => handleInputChange('username', text)}
                    placeholder="Enter name"
                    placeholderTextColor="#ffffff80"
                  />
                ) : (
                  <Text style={styles.username}>{userData.username}</Text>
                )}
                <View style={styles.patientBadge}>
                  <Text style={styles.patientBadgeText}>PATIENT</Text>
                </View>
              </View>
            </View>
            <View style={styles.citizenCard}>
              <Text style={styles.citizenLabel}>Citizen ID</Text>
              {isEditMode ? (
                <TextInput
                  style={[styles.citizenValue, styles.editableInput]}
                  value={editedData.citizenId}
                  onChangeText={(text) => handleInputChange('citizenId', text)}
                  placeholder="Enter citizen ID"
                />
              ) : (
                <Text style={styles.citizenValue}>{userData.citizenId}</Text>
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
                    <Text style={styles.detailLabel}>Email</Text>
                    <TextInput
                      style={[styles.citizenValue, styles.editableInput]}
                      value={editedData.email}
                      onChangeText={(text) => handleInputChange('email', text)}
                      placeholder="Enter email"
                    />
                    <Text style={styles.detailLabel}>Date of Birth</Text>
                    <TextInput
                      style={[styles.citizenValue, styles.editableInput]}
                      value={editedData.dateOfBirth}
                      onChangeText={(text) => handleInputChange('dateOfBirth', text)}
                      placeholder="Enter date of birth"
                    />
                    <Text style={styles.detailLabel}>Blood Type</Text>
                    <TextInput
                      style={[styles.citizenValue, styles.editableInput]}
                      value={editedData.bloodType}
                      onChangeText={(text) => handleInputChange('bloodType', text)}
                      placeholder="Enter blood type"
                    />
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
                    <Text style={styles.detailLabel}>Email</Text>
                    <Text style={styles.citizenValue}>{userData.email}</Text>
                    <Text style={styles.detailLabel}>Date of Birth</Text>
                    <Text style={styles.citizenValue}>{userData.dateOfBirth}</Text>
                    <Text style={styles.detailLabel}>Blood Type</Text>
                    <Text style={styles.citizenValue}>{userData.bloodType}</Text>
                    <Text style={styles.detailLabel}>Height</Text>
                    <Text style={styles.citizenValue}>{userData.height}</Text>
                  </>
                )}
              </View>
              <View style={styles.detailsColRight}>
                {isEditMode ? (
                  <>
                    <Text style={styles.detailLabel}>Age</Text>
                    <TextInput
                      style={[styles.citizenValue, styles.editableInput]}
                      value={editedData.age}
                      onChangeText={(text) => handleInputChange('age', text)}
                      placeholder="Enter age"
                    />
                    <Text style={styles.detailLabel}>Gender</Text>
                    <TextInput
                      style={[styles.citizenValue, styles.editableInput]}
                      value={editedData.gender}
                      onChangeText={(text) => handleInputChange('gender', text)}
                      placeholder="Enter gender"
                    />
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
                    <Text style={styles.citizenValue}>{userData.age}</Text>
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
          <TouchableOpacity style={styles.bottomBarIcon} onPress={() => navigation.navigate('Home', {userData: userData})}>
            <Ionicons name="home" size={28} color="#fff" />
          </TouchableOpacity>
          <TouchableOpacity style={styles.bottomBarIcon} onPress={() => navigation.navigate('Camera', {userData: userData})}>
            <Ionicons name="scan" size={28} color="#fff" />
          </TouchableOpacity>
          <TouchableOpacity style={styles.bottomBarIcon}>
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
});


