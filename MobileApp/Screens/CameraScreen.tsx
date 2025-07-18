import React from 'react';
import { CameraView, useCameraPermissions } from "expo-camera";
import { useEffect, useRef, useState } from "react";
import { Button, Image, Pressable, StyleSheet, Text, View, Modal, ActivityIndicator, Dimensions, TextInput, TouchableOpacity } from "react-native";
import { AntDesign } from "@expo/vector-icons";
import * as FileSystem from 'expo-file-system'
import * as ImagePicker from 'expo-image-picker'
import * as ImageManipulator from 'expo-image-manipulator';
import { bloodPressureApi } from '../api/bloodPressure';

const screenHeight = Dimensions.get('window').height;
const screenWidth = Dimensions.get('window').width;

interface BloodPressureData {
    systolic: number;
    diastolic: number;
    pulse: number;
    time: string;
}

export default function CameraScreen({ navigation, setIsCameraActive, route }: { navigation: any; setIsCameraActive: (active: boolean) => void; route: any }) {
    const [permission, requestPermission] = useCameraPermissions();
    const ref = useRef<CameraView>(null);
    const [showCamera, setShowCamera] = useState(true);
    const [imageUri, setImageUri] = useState<string | null>(null);
    const [showUploadModal, setShowUploadModal] = useState(false);
    const [showConfirmationModal, setShowConfirmationModal] = useState(false);
    const [mediaPermission, requestMediaPermission] = ImagePicker.useMediaLibraryPermissions();
    const [isProcessing, setIsProcessing] = useState(false);
    const [bloodPressureData, setBloodPressureData] = useState<BloodPressureData | null>(null);
    const [bpDataArr, setbpDataArr] = useState<BloodPressureData[]>([]);
    const [editableData, setEditableData] = useState<BloodPressureData | null>(null);

    // Initialize bpDataArr with existing readings from route params
    useEffect(() => {
        if (route.params?.existingReadings) {
            setbpDataArr(route.params.existingReadings);
        }
    }, [route.params?.existingReadings]);

    useEffect(() => {
        (async () => {
            if (!mediaPermission) {
                const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
                if (status !== 'granted') {
                    alert('Sorry, we need media library permissions to make this work!');
                }
            }
        })();
    }, []);

    useEffect(() => {
        console.log('bpDataArr has been updated:', bpDataArr);
    }, [bpDataArr]);

    const pickImage = async () => {
        try {
            const result = await ImagePicker.launchImageLibraryAsync({
                mediaTypes: ImagePicker.MediaTypeOptions.Images,
                allowsEditing: true,
                quality: 1,
            });

            if (!result.canceled && result.assets.length > 0) {
                setImageUri(result.assets[0].uri);
            }
        } catch (error) {
            console.error("Error picking image:", error);
        }
        setShowCamera(false);
        setIsCameraActive(false);
        setShowUploadModal(true);
    };

    const processImage = async () => {
        try {
            setIsProcessing(true);
            const creationTime = new Date().toLocaleTimeString();

            if (!imageUri) {
                alert('No image selected.');
                setIsProcessing(false);
                return;
            }

            // Prepare file object for upload
            const fileObj = {
                uri: imageUri,
                type: 'image/jpeg',
                name: 'image.jpg',
            };
            console.log('camera: ', fileObj);
            // Process image using the OCR API
            const ocrResponse = await bloodPressureApi.processImage(fileObj);
            console.log('ocrResp: ', ocrResponse);
            // Extract only the ocr_result
            const data = ocrResponse?.data?.ocr_result || ocrResponse?.ocr_result || ocrResponse;
            console.log('data: ', data);

            if (!data.measurement_time || data.measurement_time === "") {
                data.time = creationTime;
            }
            if (data.measurement_time) {
                data.time = data.measurement_time
            }
            console.log('data: ', data)
            setBloodPressureData(data);
            setEditableData(data);
            setShowUploadModal(false);
            setShowConfirmationModal(true);
        } catch (error) {
            console.error("Error processing image:", error);
            alert("Failed to process image. Please try again.");
            setShowUploadModal(false);
            setImageUri(null);
        } finally {
            setIsProcessing(false);
        }
    };

    const handleConfirmReadings = async () => {
        if (editableData) {
            // Save to backend using saveFromOcr
            try {
                const savePayload = {
                    systolic: editableData.systolic,
                    diastolic: editableData.diastolic,
                    pulse: editableData.pulse,
                    measurement_date: new Date().toISOString(),
                    measurement_time: editableData.time,
                    notes: '',
                };
                await bloodPressureApi.saveFromOcr(savePayload);
            } catch (error) {
                console.error('Error saving OCR record:', error);
            }
            setbpDataArr(prevData => [...prevData, editableData]);
            navigation.reset({
                index: 0,
                routes: [{
                    name: "Home",
                }],
            });
        }
    };

    const handleCancelConfirmation = () => {
        setShowConfirmationModal(false);
        setShowCamera(true);
        setIsCameraActive(true);
        setImageUri(null);
        setEditableData(null);
    };

    if (!permission) {
        return null;
    }

    if (!permission.granted) {
        return (
            <View style={styles.container}>
                <Text style={{ textAlign: "center" }}>
                    We need your permission to use the camera
                </Text>
                <Button onPress={requestPermission} title="Grant permission" />
            </View>
        );
    }

    const takePicture = async () => {
        const photo = await ref.current?.takePictureAsync();
        if (photo?.uri) {
            setImageUri(photo.uri);
            setShowUploadModal(true);
        }
        setShowCamera(false);
        setIsCameraActive(false);
    };

    const cancelUpload = () => {
        setImageUri(null);
        setShowUploadModal(false);
        setShowCamera(true);
        setIsCameraActive(true);
    };

    const renderCamera = () => {
        return (
            <CameraView
                style={styles.camera}
                ref={ref}
                mode="picture"
                facing="back"
                mute={true}
                responsiveOrientationWhenOrientationLocked
            >
                <View style={styles.shutterContainer}>
                    <Pressable onPress={pickImage}>
                        <AntDesign name="picture" size={32} color="white" />
                    </Pressable>
                    <Pressable onPress={takePicture}>
                        {({ pressed }) => (
                            <View
                                style={[
                                    styles.shutterBtn,
                                    {
                                        opacity: pressed ? 0.5 : 1,
                                    },
                                ]}
                            >
                                <View
                                    style={[
                                        styles.shutterBtnInner,
                                        {
                                            backgroundColor: "white",
                                        },
                                    ]}
                                />
                            </View>
                        )}
                    </Pressable>
                    <View style={{ width: 32 }} />
                </View>
            </CameraView>
        );
    };

    return (
        <View style={styles.container}>
            {showCamera ? (
                renderCamera()
            ) : (
                <>
                    <Modal visible={showUploadModal} transparent={true} animationType="slide">
                        <View style={styles.modalContainer}>
                            <Text style={styles.modalText}>Process this blood pressure reading?</Text>
                            {imageUri && <Image source={{ uri: imageUri }} style={styles.previewImage} />}
                            {!isProcessing ? (

                                <View style={styles.modalButtons}>
                                    
                                    <Button
                                        title="Cancel"
                                        onPress={() => cancelUpload()}
                                        color="#ff5c5c"
                                    />
                                    <Button title="Process" onPress={processImage} />
                                </View>
                            ) : (
                                <View style={styles.loadingContainer}>
                                    <ActivityIndicator size="large" color="#fff" />
                                    <Text style={styles.loadingText}>Processing image...</Text>
                                </View>
                            )}
                        </View>
                    </Modal>

                    <Modal visible={showConfirmationModal} transparent={true} animationType="slide">
                        <View style={styles.modalContainer}>
                            <Text style={styles.modalTitle}>Confirm Blood Pressure Reading</Text>
                            {imageUri && <Image source={{ uri: imageUri }} style={styles.previewImage} />}

                            <View style={[styles.readingCard, styles.shadow]}>
                                <View style={styles.readingHeaderRow}>
                                    <Text style={styles.timeText}>
                                        {editableData?.time || new Date().toLocaleTimeString()}
                                    </Text>
                                </View>
                                <View style={styles.readingValuesRow}>
                                    <View style={styles.valueContainer}>
                                        <Text style={styles.valueLabel}>Systolic</Text>
                                        <TextInput
                                            style={styles.valueInput}
                                            value={editableData?.systolic != null ? editableData.systolic.toString() : ''}
                                            onChangeText={(text) => setEditableData(prev => prev ? { ...prev, systolic: parseInt(text) || 0 } : null)}
                                            keyboardType="numeric"
                                        />
                                    </View>

                                    <View style={styles.valueContainer}>
                                        <Text style={styles.valueLabel}>Diastolic</Text>
                                        <TextInput
                                            style={styles.valueInput}
                                            value={editableData?.diastolic != null ? editableData.diastolic.toString() : ''}
                                            onChangeText={(text) => setEditableData(prev => prev ? { ...prev, diastolic: parseInt(text) || 0 } : null)}
                                            keyboardType="numeric"
                                        />
                                    </View>

                                    <View style={styles.valueContainer}>
                                        <Text style={styles.valueLabel}>Pulse</Text>
                                        <TextInput
                                            style={styles.valueInput}
                                            value={editableData?.pulse != null ? editableData.pulse.toString() : ''}
                                            onChangeText={(text) => setEditableData(prev => prev ? { ...prev, pulse: parseInt(text) || 0 } : null)}
                                            keyboardType="numeric"
                                        />
                                    </View>
                                </View>
                            </View>

                            <View style={styles.modalButtons}>
                                <TouchableOpacity
                                    style={[styles.button, styles.cancelButton]}
                                    onPress={handleCancelConfirmation}
                                >
                                    <Text style={[styles.buttonText, styles.cancelButtonText]}>Cancel</Text>
                                </TouchableOpacity>
                                <TouchableOpacity
                                    style={[styles.button, styles.confirmButton]}
                                    onPress={handleConfirmReadings}
                                >
                                    <Text style={styles.buttonText}>Confirm</Text>
                                </TouchableOpacity>

                            </View>
                        </View>
                    </Modal>
                </>
            )}
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: "#fff",
    },
    camera: {
        flex: 1,
        width: "100%",
    },
    shutterContainer: {
        position: "absolute",
        bottom: 44,
        left: 0,
        width: "100%",
        alignItems: "center",
        flexDirection: "row",
        justifyContent: "space-between",
        paddingHorizontal: 30,
    },
    shutterBtn: {
        backgroundColor: "transparent",
        borderWidth: 5,
        borderColor: "white",
        width: 85,
        height: 85,
        borderRadius: 45,
        alignItems: "center",
        justifyContent: "center",
    },
    shutterBtnInner: {
        width: 70,
        height: 70,
        borderRadius: 50,
    },
    modalContainer: {
        flex: 1,
        backgroundColor: "rgba(0, 0, 0, 0.8)",
        justifyContent: "center",
        alignItems: "center",
        padding: 20,
    },
    modalText: {
        fontSize: 18,
        color: "#fff",
        marginBottom: 20,
        fontWeight: 'bold',
    },
    modalTitle: {
        fontSize: 24,
        color: "#fff",
        marginBottom: 20,
        fontWeight: 'bold',
        textAlign: 'center',
    },
    readingCard: {
        backgroundColor: '#fff',
        borderRadius: 20,
        borderWidth: 1,
        borderColor: '#222',
        padding: 20,
        width: '100%',
        marginVertical: 20,
    },
    shadow: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.08,
        shadowRadius: 4,
        elevation: 2,
    },
    readingHeaderRow: {
        marginBottom: 10,
    },
    timeText: {
        fontSize: 16,
        color: '#222',
        fontWeight: '400',
    },
    readingValuesRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginTop: 8,
    },
    valueContainer: {
        alignItems: 'center',
        flex: 1,
    },
    valueLabel: {
        fontSize: 16,
        color: '#222',
        fontWeight: '600',
        marginBottom: 4,
    },
    valueInput: {
        fontSize: 28,
        fontWeight: 'bold',
        color: '#222',
        textAlign: 'center',
        padding: 5,
        minWidth: 80,
        borderWidth: 1,
        borderColor: '#808080',
        borderRadius: 10,
        backgroundColor: '#f2f2f2',
    },
    previewImage: {
        width: 200,
        height: 200,
        marginBottom: 20,
        borderRadius: 10,
    },
    modalButtons: {
        flexDirection: "row",
        justifyContent: "space-between",
        width: "100%",
        marginTop: 20,
        gap: 20,
    },
    button: {
        flex: 1,
        paddingVertical: 12,
        borderRadius: 25,
        alignItems: 'center',
        justifyContent: 'center',
    },
    confirmButton: {
        backgroundColor: '#4662e6',
    },
    cancelButton: {
        backgroundColor: 'transparent',
        borderWidth: 1,
        borderColor: '#ff5c5c',
    },
    buttonText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: 'bold',
    },
    cancelButtonText: {
        color: '#ff5c5c',
    },
    loadingContainer: {
        alignItems: 'center',
        marginTop: 20,
    },
    loadingText: {
        color: '#fff',
        marginTop: 10,
        fontSize: 16,
    },
});