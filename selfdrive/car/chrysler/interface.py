#!/usr/bin/env python3
from cereal import car
from selfdrive.car.chrysler.values import CAR
from selfdrive.car import STD_CARGO_KG, scale_rot_inertia, scale_tire_stiffness, gen_empty_fingerprint, get_safety_config
from selfdrive.car.interfaces import CarInterfaceBase


class CarInterface(CarInterfaceBase):
  @staticmethod
  def get_params(candidate, fingerprint=gen_empty_fingerprint(), car_fw=None, disable_radar=False):
    ret = CarInterfaceBase.get_std_params(candidate, fingerprint)
    ret.carName = "chrysler"
    ret.safetyConfigs = [get_safety_config(car.CarParams.SafetyModel.chrysler)]

    # Speed conversion:              20, 45 mph
    ret.wheelbase = 3.089  # in meters for Pacifica Hybrid 2017
    ret.steerRatio = 16.2  # Pacifica Hybrid 2017
    ret.mass = 2242. + STD_CARGO_KG  # kg curb weight Pacifica Hybrid 2017
    ret.lateralTuning.pid.kpBP, ret.lateralTuning.pid.kiBP = [[9., 20.], [9., 20.]]
    ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.15, 0.30], [0.03, 0.05]]
    ret.lateralTuning.pid.kf = 0.00006   # full torque for 10 deg at 80mph means 0.00007818594
    ret.steerActuatorDelay = 0.1
    ret.steerRateCost = 0.7
    ret.steerLimitTimer = 0.4
    ret.minSteerSpeed = 3.8  # m/s


    if candidate in (CAR.JEEP_CHEROKEE, CAR.JEEP_CHEROKEE_2019):
      ret.wheelbase = 2.91  # in meters
      ret.steerRatio = 12.7
      ret.steerActuatorDelay = 0.2  # in seconds

    ret.centerToFront = ret.wheelbase * 0.44

    if candidate in (CAR.RAM_1500):
      ret.wheelbase = 3.67  # 2021 Ram 1500 Short box crew cab
      ret.steerRatio = 16.1  # just a guess
      ret.mass = 2651.247 + STD_CARGO_KG  # kg curb weight 2021 Ram 1500 shortbox crew limited
      MAX_TORQUE = 3.6
      ret.lateralTuning.init('torque')
      ret.lateralTuning.torque.useSteeringAngle = True
      ret.lateralTuning.torque.kp = 2.0 / MAX_TORQUE
      ret.lateralTuning.torque.kf = 1.0 / MAX_TORQUE
      ret.lateralTuning.torque.ki = 0.5 / MAX_TORQUE
      ret.lateralTuning.torque.friction = 0.001
      ret.steerActuatorDelay = 0.16
      ret.steerRateCost = 1.0
      ret.centerToFront = ret.wheelbase * 0.4 # just a guess
      ret.minSteerSpeed = 14.5

    if candidate in (CAR.RAM_2500):
      ret.wheelbase = 3.785  # in meters
      ret.steerRatio = 23  # just a guess
      ret.mass = 3405. + STD_CARGO_KG  # kg curb weight 2021 Ram 2500
      ret.lateralTuning.pid.kpBP, ret.lateralTuning.pid.kiBP = [[0.], [0.,]]
      ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.15], [0.015,]]
      ret.steerActuatorDelay = 0.1
      ret.steerRateCost = 0.5  # may need tuning
      ret.centerToFront = ret.wheelbase * 0.38 # calculated from 100% - (front axle weight/total weight)
      ret.minSteerSpeed = 16

    if candidate in (CAR.PACIFICA_2019_HYBRID, CAR.PACIFICA_2020, CAR.JEEP_CHEROKEE_2019):
      # TODO allow 2019 cars to steer down to 13 m/s if already engaged.
      ret.minSteerSpeed = 17.5  # m/s 17 on the way up, 13 on the way down once engaged.

    # starting with reasonable value for civic and scaling by mass and wheelbase
    ret.rotationalInertia = scale_rot_inertia(ret.mass, ret.wheelbase)

    # TODO: start from empirically derived lateral slip stiffness for the civic and scale by
    # mass and CG position, so all cars will have approximately similar dyn behaviors
    ret.tireStiffnessFront, ret.tireStiffnessRear = scale_tire_stiffness(ret.mass, ret.wheelbase, ret.centerToFront)

    ret.enableBsm = 720 in fingerprint[0]

    return ret

  # returns a car.CarState
  def _update(self, c):
    ret = self.CS.update(self.cp, self.cp_cam)

    ret.steeringRateLimited = self.CC.steer_rate_limited if self.CC is not None else False

    # events
    events = self.create_common_events(ret, extra_gears=[car.CarState.GearShifter.low])

    # Low speed steer alert hysteresis logic
    if self.CP.minSteerSpeed > 0. and ret.vEgo < (self.CP.minSteerSpeed -0.5):
      self.low_speed_alert = True
    elif ret.vEgo > (self.CP.minSteerSpeed):
      self.low_speed_alert = False
    if self.low_speed_alert:
      events.add(car.CarEvent.EventName.belowSteerSpeed)

    ret.events = events.to_msg()

    return ret

  # pass in a car.CarControl
  # to be called @ 100hz
  def apply(self, c):

    if (self.CS.frame == -1):
      return car.CarControl.Actuators.new_message(), []  # if we haven't seen a frame 220, then do not update.

    return self.CC.update(c.enabled, self.CS, self.frame, c.actuators, c.cruiseControl.cancel, c.hudControl.visualAlert, c.hudControl.leftLaneVisible, c.hudControl.rightLaneVisible, c.hudControl.leadVisible, c.hudControl.leftLaneDepart, c.hudControl.rightLaneDepart)
